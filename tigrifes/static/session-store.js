"use strict";
(() => {
  const machine = typeof module !== "undefined" && module.exports ? require("./machine.js") : globalThis.TigrifesMachine;

  function revision() {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    // Este identificador detecta alterações locais; não participa do sorteio.
    return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }

  class SessionChangedError extends Error {
    constructor() {
      super("A sessão mudou em outra aba. Os dados foram sincronizados; tente novamente.");
    }
  }

  class SessionStore {
    constructor(storage, key) {
      this.storage = storage;
      this.key = key;
      this.persistent = Boolean(storage);
      this.memory = null;
      this.recovered = false;
    }

    read() {
      let raw;
      try { raw = this.persistent ? this.storage.getItem(this.key) : this.memory; }
      catch (_) { this.persistent = false; raw = this.memory; }
      if (!raw) return null;
      try {
        const checkpoint = JSON.parse(raw);
        return { checkpoint, session: machine.restore(checkpoint) };
      } catch (_) {
        this.recovered = true;
        return null;
      }
    }

    save(session) {
      const checkpoint = { version: 1, seed: session.seed, rounds: session.rounds, revision: revision() };
      this.memory = JSON.stringify(checkpoint);
      if (this.persistent) {
        try { this.storage.setItem(this.key, this.memory); }
        catch (_) { this.persistent = false; }
      }
      return { checkpoint, state: machine.publicState(session) };
    }

    load() {
      const current = this.read();
      if (!current) return this.save(machine.createSession());
      this.memory = JSON.stringify(current.checkpoint);
      return { checkpoint: current.checkpoint, state: machine.publicState(current.session) };
    }

    change(expectedRevision, operation) {
      const current = this.read();
      if (!current || current.checkpoint.revision !== expectedRevision) throw new SessionChangedError();
      const session = operation(current.session);
      return this.save(session);
    }

    spin(expectedRevision) {
      return this.change(expectedRevision, (session) => {
        machine.advance(session);
        return session;
      });
    }

    reset(seed, expectedRevision) {
      machine.validateSeed(seed);
      return this.change(expectedRevision, () => machine.createSession(seed));
    }
  }

  const api = Object.freeze({ SessionStore, SessionChangedError });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.TigrifesSessions = api;
})();
