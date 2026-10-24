"use strict";
// Teste de integração da interface em DOM mínimo. Não substitui inspeção visual.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { webcrypto } = require("node:crypto");

class Element {
  constructor() {
    this.children = [];
    this.attributes = {};
    this.listeners = {};
    this.classList = { toggle() {} };
    this.open = false;
    this.textContent = "";
  }
  setAttribute(name, value) { this.attributes[name] = value; }
  getAttribute(name) { return this.attributes[name]; }
  append(child) { this.children.push(child); }
  replaceChildren() { this.children = []; }
  addEventListener(name, callback) { this.listeners[name] = callback; }
  async emit(name) { return this.listeners[name]({ preventDefault() {} }); }
  showModal() { this.open = true; }
  close() { this.open = false; }
  focus() { this.focused = true; }
}

function storage() {
  const data = new Map();
  return { getItem: (key) => data.get(key) ?? null, setItem: (key, value) => data.set(key, value) };
}

function interfaceSession(disk = storage(), pathname = "/TigrIFES/") {
  const nodes = new Map();
  const byId = (id) => {
    if (!nodes.has(id)) nodes.set(id, new Element());
    return nodes.get(id);
  };
  const symbols = Array.from({ length: 9 }, () => new Element());
  byId("board").querySelectorAll = () => symbols;
  byId("board").setAttribute("data-symbols", JSON.stringify({
    A: { emoji: "🍒", name: "cereja" }, B: { emoji: "🍋", name: "limão" },
    C: { emoji: "🍇", name: "uva" }, D: { emoji: "🍉", name: "melancia" }, E: { emoji: "🐯", name: "tigre" },
  }));
  byId("balance-chart").querySelector = () => new Element();
  const listeners = {};
  const context = vm.createContext({
    document: { getElementById: byId, createElement: () => new Element(),
      currentScript: { src: `https://example.test${pathname}assets/app-static.js` } },
    localStorage: disk, URL, Intl, crypto: webcrypto,
    navigator: { locks: { request: async (_, operation) => operation() } },
    matchMedia: () => ({ matches: true }), setTimeout: (callback) => callback(),
    addEventListener: (name, callback) => { listeners[name] = callback; },
  });
  for (const filename of ["machine.js", "session-store.js", "app-static.js"]) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, "../../tigrifes/static", filename), "utf8"), context, { filename });
  }
  return { byId, context, listeners };
}

test("A interface inicializa, gira uma vez com clique duplo e restaura o histórico", async () => {
  const disk = storage();
  const first = interfaceSession(disk);
  assert.equal(first.byId("balance").textContent, "100");
  assert.equal(first.byId("spin-button").disabled, false);
  await Promise.all([first.byId("spin-button").emit("click"), first.byId("spin-button").emit("click")]);
  assert.equal(first.byId("round-count").textContent, 1);
  assert.equal(first.byId("balance").textContent, "99");
  assert.match(first.byId("result-message").textContent, /Rodada 1/);
  assert.equal(first.byId("history-body").children.length, 1);
  const reloaded = interfaceSession(disk);
  assert.equal(reloaded.byId("round-count").textContent, 1);
  assert.equal(reloaded.byId("balance").textContent, "99");
  assert.equal(reloaded.byId("history-body").children[0].children.length, 5);
});

test("O diálogo reinicia a sessão com a semente escolhida e devolve o foco", async () => {
  const app = interfaceSession();
  await app.byId("spin-button").emit("click");
  await app.byId("open-reset").emit("click");
  assert.equal(app.byId("reset-dialog").open, true);
  app.byId("seed-input").value = "42";
  await app.byId("reset-form").emit("submit");
  assert.equal(app.byId("reset-dialog").open, false);
  assert.equal(app.byId("balance").textContent, "100");
  assert.equal(app.byId("seed-label").textContent, 42);
  assert.equal(app.byId("round-count").textContent, 0);
  assert.equal(app.byId("spin-button").focused, true);
  assert.equal(app.byId("spin-button").disabled, false);
});

test("Abas sincronizam o saldo e instalações em caminhos distintos ficam isoladas", async () => {
  const disk = storage();
  const first = interfaceSession(disk);
  const second = interfaceSession(disk);
  const otherProject = interfaceSession(disk, "/OutroProjeto/");
  await first.byId("spin-button").emit("click");
  second.listeners.storage({ key: "tigrifes:session:v1:/TigrIFES/" });
  assert.equal(second.byId("balance").textContent, "99");
  assert.equal(otherProject.byId("balance").textContent, "100");
});

test("Sem armazenamento a interface continua jogável e explica a duração da sessão", async () => {
  const app = interfaceSession({ getItem() { throw Error("blocked"); } });
  assert.match(app.byId("session-storage-note").textContent, /bloqueou o armazenamento/);
  await app.byId("spin-button").emit("click");
  assert.equal(app.byId("balance").textContent, "99");
});
