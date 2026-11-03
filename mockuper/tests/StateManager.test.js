import test from 'node:test';
import assert from 'node:assert/strict';
import { StateManager, MAX_HISTORY } from '../js/modules/StateManager.js';

class MemoryStorage {
    constructor() {
        this.values = new Map();
    }
    getItem(key) {
        return this.values.has(key) ? this.values.get(key) : null;
    }
    setItem(key, value) {
        this.values.set(key, String(value));
    }
    removeItem(key) {
        this.values.delete(key);
    }
    clear() {
        this.values.clear();
    }
}

function setupStorage(storage = new MemoryStorage()) {
    globalThis.localStorage = storage;
    return storage;
}

test('starts with a single page and an initial undo snapshot', () => {
    setupStorage();
    const state = new StateManager();
    assert.equal(state.pages.length, 1);
    assert.equal(state.history.length, 1);
    assert.equal(state.historyIndex, 0);
    assert.equal(state.canUndo(), false);
});

test('adds an element and undoes and redoes it', () => {
    setupStorage();
    const state = new StateManager();
    state.addElement('button');
    assert.equal(state.getCurrentPage().elements.length, 1);
    assert.equal(state.canUndo(), true);

    state.undo();
    assert.equal(state.getCurrentPage().elements.length, 0);
    assert.equal(state.canRedo(), true);

    state.redo();
    assert.equal(state.getCurrentPage().elements.length, 1);
});

test('deletes an element and undoes and redoes the deletion', () => {
    setupStorage();
    const state = new StateManager();
    state.addElement('text');
    const id = state.getCurrentPage().elements[0].id;

    state.deleteElement(id);
    assert.equal(state.getCurrentPage().elements.length, 0);
    state.undo();
    assert.equal(state.getCurrentPage().elements.length, 1);
    state.redo();
    assert.equal(state.getCurrentPage().elements.length, 0);
});

test('updates an element and records the update in history', () => {
    setupStorage();
    const state = new StateManager();
    state.addElement('button');
    const id = state.getCurrentPage().elements[0].id;

    state.updateElement(id, { text: 'Save' });
    state.saveHistory();
    assert.equal(state.getCurrentPage().elements[0].text, 'Save');
    state.undo();
    assert.equal(state.getCurrentPage().elements[0].text, 'Button');
});

test('history never exceeds MAX_HISTORY and the index stays at the newest snapshot', () => {
    setupStorage();
    const state = new StateManager();

    for (let i = 0; i < MAX_HISTORY + 25; i++) {
        state.addElement('button');
    }

    assert.equal(state.history.length, MAX_HISTORY);
    assert.equal(state.historyIndex, MAX_HISTORY - 1);
    assert.equal(state.canRedo(), false);
    assert.equal(state.canUndo(), true);
});

test('undo and redo remain usable after history is capped', () => {
    setupStorage();
    const state = new StateManager();

    for (let i = 0; i < MAX_HISTORY + 10; i++) {
        state.addElement('button');
    }

    state.undo();
    assert.equal(state.getCurrentPage().elements.length, MAX_HISTORY + 9);
    state.redo();
    assert.equal(state.getCurrentPage().elements.length, MAX_HISTORY + 10);
});

test('JSON export and import round-trip project state', () => {
    setupStorage();
    const state = new StateManager();
    state.addElement('button');
    state.updateElement(state.getCurrentPage().elements[0].id, { text: 'Launch' });
    const json = state.exportToJSON();

    const imported = new StateManager();
    assert.equal(imported.importFromJSON(json), true);
    assert.equal(imported.pages.length, 1);
    assert.equal(imported.getCurrentPage().elements.length, 1);
    assert.equal(imported.getCurrentPage().elements[0].text, 'Launch');
});

test('invalid import JSON is rejected without changing state', () => {
    setupStorage();
    const state = new StateManager();
    assert.equal(state.importFromJSON('not json'), false);
    assert.equal(state.pages.length, 1);
});

test('missing pages in imported JSON is rejected', () => {
    setupStorage();
    const state = new StateManager();
    assert.equal(state.importFromJSON(JSON.stringify({ version: '1.0' })), false);
});

test('a throwing setItem does not interrupt state changes', () => {
    const throwingStorage = new MemoryStorage();
    throwingStorage.setItem = () => {
        throw new Error('Storage quota exceeded');
    };
    setupStorage(throwingStorage);
    const state = new StateManager();
    let warningCalls = 0;
    state.onStorageError(() => warningCalls++);

    state.addElement('button');
    state.deleteElement(state.getCurrentPage().elements[0].id);
    state.addElement('text');

    assert.equal(state.getCurrentPage().elements.length, 1);
    assert.equal(warningCalls, 1);
});

test('storage warning is emitted only once across repeated failures', () => {
    const throwingStorage = new MemoryStorage();
    throwingStorage.setItem = () => {
        throw new Error('Storage blocked');
    };
    setupStorage(throwingStorage);
    const state = new StateManager();
    let warningCalls = 0;
    state.onStorageError(() => warningCalls++);

    state.notify();
    state.notify();
    assert.equal(warningCalls, 1);
});
