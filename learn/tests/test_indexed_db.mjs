import assert from "node:assert/strict";
import test from "node:test";
import { indexedDB } from "fake-indexeddb";
import {
  LEARN_DATABASE_NAME,
  StorageMigrationError,
  StorageQuotaError,
  StorageSecurityError,
  StorageTransactionError,
  StorageUnavailableError,
  openLearnStorage,
} from "../public/js/learn-storage.js";

function freshIndexedDB() {
  return indexedDB;
}

async function deleteDatabase() {
  await new Promise((resolve, reject) => {
    const request = freshIndexedDB().deleteDatabase(LEARN_DATABASE_NAME);
    request.onsuccess = request.onerror = request.onblocked = () => resolve();
  });
}

test.beforeEach(deleteDatabase);
test.afterEach(deleteDatabase);

test("initializes the metadata store and supports CRUD after a real commit", async () => {
  const storage = await openLearnStorage({ indexedDB: freshIndexedDB() });
  await storage.put({ key: "schema-version", value: 1 });
  assert.deepEqual(await storage.get("schema-version"), { key: "schema-version", value: 1 });
  assert.deepEqual(await storage.list(), [{ key: "schema-version", value: 1 }]);
  await storage.delete("schema-version");
  assert.deepEqual(await storage.list(), []);
  await storage.put({ key: "temporary", value: true });
  await storage.clear();
  assert.deepEqual(await storage.list(), []);
  storage.close();
});

test("repeated initialization is safe and reopens the same database", async () => {
  const first = await openLearnStorage({ indexedDB: freshIndexedDB() });
  await first.put({ key: "persisted", value: "yes" });
  first.close();
  const second = await openLearnStorage({ indexedDB: freshIndexedDB() });
  assert.deepEqual(await second.get("persisted"), { key: "persisted", value: "yes" });
  second.close();
});

test("runs ordered migrations during a version upgrade", async () => {
  const order = [];
  const first = await openLearnStorage({ indexedDB: freshIndexedDB() });
  first.close();
  const upgraded = await openLearnStorage({
    indexedDB: freshIndexedDB(),
    version: 3,
    migrations: [
      { version: 2, migrate() { order.push(2); } },
      { version: 3, migrate() { order.push(3); } },
    ],
  });
  assert.deepEqual(order, [2, 3]);
  upgraded.close();
});

test("failed migrations reject initialization", async () => {
  const first = await openLearnStorage({ indexedDB: freshIndexedDB() });
  first.close();
  await assert.rejects(
    openLearnStorage({
      indexedDB: freshIndexedDB(),
      version: 2,
      migrations: [{ version: 2, migrate() { throw new Error("broken migration"); } }],
    }),
    StorageMigrationError,
  );
});

test("reports unavailable IndexedDB", async () => {
  await assert.rejects(openLearnStorage({ indexedDB: undefined }), StorageUnavailableError);
});

test("classifies quota failures and transaction failures", async () => {
  const storage = await openLearnStorage({ indexedDB: freshIndexedDB() });
  const originalTransaction = storage.database.transaction.bind(storage.database);
  storage.database.transaction = () => {
    const error = new DOMException("quota", "QuotaExceededError");
    throw error;
  };
  await assert.rejects(storage.put({ key: "quota", value: true }), StorageQuotaError);
  storage.database.transaction = originalTransaction;
  await assert.rejects(storage.get("missing", "unknown"), StorageTransactionError);
  storage.close();
});

test("rejects credential-like metadata and never writes it", async () => {
  const storage = await openLearnStorage({ indexedDB: freshIndexedDB() });
  await assert.rejects(storage.put({ key: "edu_token", value: "secret" }), StorageSecurityError);
  await assert.rejects(storage.put({ key: "safe", value: { password: "secret" } }), StorageSecurityError);
  assert.deepEqual(await storage.list(), []);
  storage.close();
});

test("reopening at a newer version preserves metadata", async () => {
  const first = await openLearnStorage({ indexedDB: freshIndexedDB() });
  await first.put({ key: "keep", value: { retained: true } });
  first.close();
  const second = await openLearnStorage({
    indexedDB: freshIndexedDB(),
    version: 2,
    migrations: [{ version: 2, migrate() {} }],
  });
  assert.deepEqual(await second.get("keep"), { key: "keep", value: { retained: true } });
  second.close();
});
