"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const machine = require("../../tigrifes/static/machine.js");
const { SessionStore, SessionChangedError } = require("../../tigrifes/static/session-store.js");

function storage() {
  const data = new Map();
  return { getItem: (key) => data.get(key) ?? null, setItem: (key, value) => data.set(key, value) };
}

test("Os 125 resultados têm exatamente os pagamentos e a esperança do modelo", () => {
  const counts = new Map();
  let total = 0;
  for (let a = 0; a < 5; a++) for (let b = 0; b < 5; b++) for (let c = 0; c < 5; c++) {
    const result = machine.fromStops([a, b, c]);
    counts.set(result.prize, (counts.get(result.prize) || 0) + 1);
    total += result.profit;
    assert.equal(result.profit, result.prize - 1);
  }
  assert.deepEqual([...counts].sort((a, b) => a[0] - b[0]), [[0, 120], [5, 1], [10, 1], [15, 1], [25, 1], [50, 1]]);
  assert.equal(total / 125, -.16);
  assert.deepEqual(machine.fromStops([4, 0, 1]).board, [["E", "A", "B"], ["A", "B", "C"], ["B", "C", "D"]]);
});

test("Sementes e paradas inválidas são recusadas", () => {
  for (const seed of [-1, 2 ** 32, 1.5, true, "2026", NaN]) {
    assert.throws(() => machine.createSession(seed), RangeError);
  }
  for (const stops of [[0, 1], [0, 0, 5], [0, -.1, 2], [true, 0, 0]]) {
    assert.throws(() => machine.fromStops(stops), RangeError);
  }
});

test("Restaurar a sessão recompõe o histórico e mantém o próximo sorteio", () => {
  const disk = storage();
  const first = new SessionStore(disk, "game");
  let envelope = first.load();
  for (let i = 0; i < 40; i++) envelope = first.spin(envelope.checkpoint.revision);
  const second = new SessionStore(disk, "game");
  const loaded = second.load();
  assert.deepEqual(loaded, envelope);
  assert.equal(loaded.state.history.length, 12);
  assert.equal(loaded.state.trajectory.length, 41);
  const expected = machine.createSession(2026);
  for (let i = 0; i < 41; i++) machine.advance(expected);
  const next = second.spin(loaded.checkpoint.revision);
  assert.deepEqual(next.state, machine.publicState(expected));
});

test("Uma revisão antiga não aplica um segundo giro nem sobrescreve um reset", () => {
  const disk = storage();
  const first = new SessionStore(disk, "game");
  const second = new SessionStore(disk, "game");
  const original = first.load();
  const spun = first.spin(original.checkpoint.revision);
  assert.throws(() => second.spin(original.checkpoint.revision), SessionChangedError);
  assert.throws(() => second.reset(42, original.checkpoint.revision), SessionChangedError);
  assert.deepEqual(second.load(), spun);
  const reset = second.reset(42, spun.checkpoint.revision);
  assert.equal(reset.state.balance, 100);
  assert.equal(reset.state.rounds, 0);
  assert.equal(reset.state.seed, 42);
});

test("Armazenamento bloqueado ou cheio permite continuar em memória", () => {
  for (const disk of [null, { getItem() { throw Error("blocked"); } },
    { getItem() { return null; }, setItem() { throw Error("full"); } }]) {
    const store = new SessionStore(disk, "game");
    const initial = store.load();
    const played = store.spin(initial.checkpoint.revision);
    assert.equal(played.state.rounds, 1);
    assert.equal(store.persistent, false);
    assert.deepEqual(store.load(), played);
  }
});

test("Sessão corrompida é recuperada e o saldo salvo não é usado como entrada", () => {
  const disk = storage();
  disk.setItem("game", "{invalid");
  const store = new SessionStore(disk, "game");
  assert.equal(store.load().state.balance, 100);
  assert.equal(store.recovered, true);
  disk.setItem("game", JSON.stringify({ version: 1, seed: 2026, rounds: 1, revision: "valid", balance: 999999 }));
  assert.equal(store.load().state.balance, 99);
  disk.setItem("game", JSON.stringify({ version: 1, seed: 2026, rounds: 501, revision: "invalid" }));
  assert.equal(store.load().state.rounds, 0);
});

test("As sessões param ao esgotar o saldo ou completar 500 rodadas", () => {
  let foundExhaustion = false;
  let foundLimit = false;
  for (let seed = 0; seed < 20 && !(foundExhaustion && foundLimit); seed++) {
    const session = machine.createSession(seed);
    while (!machine.publicState(session).finished) machine.advance(session);
    assert.ok(session.balance >= 0);
    assert.ok(session.rounds <= 500);
    foundExhaustion ||= session.balance === 0;
    foundLimit ||= session.rounds === 500;
    const final = JSON.stringify(machine.publicState(session));
    assert.throws(() => machine.advance(session), /encerrada/);
    assert.equal(JSON.stringify(machine.publicState(session)), final);
  }
  assert.ok(foundExhaustion && foundLimit);
});
