export const LEARN_DATABASE_NAME = "learn-local";
export const LEARN_DATABASE_VERSION = 1;
export const METADATA_STORE_NAME = "meta";

const SENSITIVE_NAME = /(?:token|password|secret|credential|authorization|session)/i;

export class LearnStorageError extends Error {
  constructor(message, options = {}) {
    super(message, options);
    this.name = "LearnStorageError";
  }
}

export class StorageUnavailableError extends LearnStorageError {
  constructor(message = "IndexedDB is unavailable in this environment.") {
    super(message);
    this.name = "StorageUnavailableError";
  }
}

export class StorageInitializationError extends LearnStorageError {
  constructor(message, options = {}) {
    super(message, options);
    this.name = "StorageInitializationError";
  }
}

export class StorageMigrationError extends StorageInitializationError {
  constructor(message, options = {}) {
    super(message, options);
    this.name = "StorageMigrationError";
  }
}

export class StorageQuotaError extends LearnStorageError {
  constructor(message = "IndexedDB storage quota was exceeded.", options = {}) {
    super(message, options);
    this.name = "StorageQuotaError";
  }
}

export class StorageTransactionError extends LearnStorageError {
  constructor(message, options = {}) {
    super(message, options);
    this.name = "StorageTransactionError";
  }
}

export class StorageSecurityError extends LearnStorageError {
  constructor(message = "Sensitive authentication data cannot be stored.") {
    super(message);
    this.name = "StorageSecurityError";
  }
}

const initialMigration = {
  version: 1,
  migrate(database) {
    if (!database.objectStoreNames.contains(METADATA_STORE_NAME)) {
      database.createObjectStore(METADATA_STORE_NAME, { keyPath: "key" });
    }
  },
};

function isQuotaError(error) {
  return error && error.name === "QuotaExceededError";
}

function asError(error) {
  return error instanceof Error ? error : new Error(String(error || "Unknown error"));
}

function hasSensitiveName(value, seen = new Set()) {
  if (!value || typeof value !== "object") return false;
  if (seen.has(value)) return false;
  seen.add(value);
  if (Array.isArray(value)) return value.some((entry) => hasSensitiveName(entry, seen));
  return Object.entries(value).some(
    ([key, entry]) => SENSITIVE_NAME.test(key) || hasSensitiveName(entry, seen),
  );
}

function assertSafeKey(key) {
  if (typeof key === "string" && SENSITIVE_NAME.test(key)) {
    throw new StorageSecurityError();
  }
}

function assertSafeValue(value) {
  if (hasSensitiveName(value)) throw new StorageSecurityError();
}

function normalizeMigrations(migrations) {
  const all = [initialMigration, ...(migrations || [])]
    .map((migration) => {
      if (typeof migration === "function") return { version: 1, migrate: migration };
      return migration;
    })
    .sort((left, right) => left.version - right.version);
  const seen = new Set();
  for (const migration of all) {
    if (!Number.isInteger(migration.version) || migration.version < 1) {
      throw new StorageInitializationError("Migration versions must be positive integers.");
    }
    if (seen.has(migration.version)) {
      throw new StorageInitializationError(`Duplicate migration version ${migration.version}.`);
    }
    if (typeof migration.migrate !== "function") {
      throw new StorageInitializationError(`Migration ${migration.version} is not callable.`);
    }
    seen.add(migration.version);
  }
  return all;
}

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error || new Error("IndexedDB request failed."));
  });
}

function transactionResult(transaction, requestPromise) {
  return new Promise((resolve, reject) => {
    let result;
    let requestError;
    requestPromise.then((value) => {
      result = value;
    }, (error) => {
      requestError = error;
    });
    transaction.oncomplete = () => {
      if (requestError) reject(requestError);
      else resolve(result);
    };
    transaction.onerror = () => {
      reject(transaction.error || requestError || new Error("IndexedDB transaction failed."));
    };
    transaction.onabort = () => {
      reject(transaction.error || requestError || new Error("IndexedDB transaction aborted."));
    };
  });
}

function operationError(operation, error) {
  const cause = asError(error);
  if (isQuotaError(cause)) {
    return new StorageQuotaError(`IndexedDB ${operation} exceeded the storage quota.`, { cause });
  }
  return new StorageTransactionError(`IndexedDB ${operation} failed.`, { cause });
}

export async function openLearnStorage(options = {}) {
  const indexedDB = options.indexedDB === undefined ? globalThis.indexedDB : options.indexedDB;
  if (!indexedDB || typeof indexedDB.open !== "function") {
    throw new StorageUnavailableError();
  }

  const version = options.version || LEARN_DATABASE_VERSION;
  const migrations = normalizeMigrations(options.migrations);
  if (!Number.isInteger(version) || version < 1) {
    throw new StorageInitializationError("The database version must be a positive integer.");
  }
  if (migrations.some((migration) => migration.version > version)) {
    throw new StorageInitializationError("A migration cannot target a future database version.");
  }

  const database = await new Promise((resolve, reject) => {
    let request;
    try {
      request = indexedDB.open(LEARN_DATABASE_NAME, version);
    } catch (error) {
      reject(new StorageInitializationError("IndexedDB could not be opened.", { cause: asError(error) }));
      return;
    }

    request.onupgradeneeded = (event) => {
      try {
        for (const migration of migrations) {
          if (migration.version > event.oldVersion && migration.version <= event.newVersion) {
            migration.migrate(event.target.result, event.target.transaction, event.oldVersion);
          }
        }
      } catch (error) {
        request.transaction.abort();
        reject(new StorageMigrationError("IndexedDB migration failed.", { cause: asError(error) }));
      }
    };
    request.onblocked = () => {
      reject(new StorageInitializationError("IndexedDB upgrade is blocked by another connection."));
    };
    request.onerror = () => {
      reject(new StorageInitializationError("IndexedDB could not be initialized.", {
        cause: request.error || undefined,
      }));
    };
    request.onsuccess = () => resolve(request.result);
  }).catch((error) => {
    if (error instanceof LearnStorageError) throw error;
    throw new StorageInitializationError("IndexedDB initialization failed.", { cause: asError(error) });
  });

  database.onversionchange = () => database.close();
  return new LearnStorage(database);
}

export class LearnStorage {
  constructor(database) {
    this.database = database;
  }

  async get(key, storeName = METADATA_STORE_NAME) {
    assertSafeKey(key);
    try {
      const transaction = this.database.transaction(storeName, "readonly");
      return await transactionResult(transaction, requestResult(transaction.objectStore(storeName).get(key)));
    } catch (error) {
      throw operationError("read", error);
    }
  }

  async put(value, storeName = METADATA_STORE_NAME) {
    assertSafeValue(value);
    if (!value || typeof value.key !== "string") {
      throw new StorageTransactionError("Stored metadata must include a string key.");
    }
    assertSafeKey(value.key);
    try {
      const transaction = this.database.transaction(storeName, "readwrite");
      return await transactionResult(transaction, requestResult(transaction.objectStore(storeName).put(value)));
    } catch (error) {
      throw operationError("write", error);
    }
  }

  async delete(key, storeName = METADATA_STORE_NAME) {
    assertSafeKey(key);
    try {
      const transaction = this.database.transaction(storeName, "readwrite");
      return await transactionResult(transaction, requestResult(transaction.objectStore(storeName).delete(key)));
    } catch (error) {
      throw operationError("delete", error);
    }
  }

  async list(storeName = METADATA_STORE_NAME) {
    try {
      const transaction = this.database.transaction(storeName, "readonly");
      return await transactionResult(transaction, requestResult(transaction.objectStore(storeName).getAll()));
    } catch (error) {
      throw operationError("list", error);
    }
  }

  async clear(storeName = METADATA_STORE_NAME) {
    try {
      const transaction = this.database.transaction(storeName, "readwrite");
      return await transactionResult(transaction, requestResult(transaction.objectStore(storeName).clear()));
    } catch (error) {
      throw operationError("clear", error);
    }
  }

  close() {
    this.database.close();
  }
}
