"use strict";
// Implementação do algoritmo MT19937 com inicialização inteira e randrange(5)
// compatíveis com CPython 3.13, para sementes entre 0 e 2**32 - 1.
// Referências e licença: LICENSES/MT19937.txt e README.md.
(() => {
  const SYMBOLS = Object.freeze(["A", "B", "C", "D", "E"]);
  const PAYOUTS = Object.freeze({ A: 5, B: 10, C: 15, D: 25, E: 50 });
  const INITIAL_BALANCE = 100;
  const MAX_ROUNDS = 500;

  function validateSeed(seed) {
    if (!Number.isInteger(seed) || seed < 0 || seed > 0xffffffff) {
      throw new RangeError("A semente deve ser um inteiro entre 0 e 4.294.967.295.");
    }
    return seed;
  }

  class PythonRandom {
    constructor(seed) {
      validateSeed(seed);
      this.state = new Uint32Array(624);
      this.state[0] = 19650218;
      for (let i = 1; i < 624; i++) {
        const previous = this.state[i - 1];
        this.state[i] = (Math.imul(1812433253, previous ^ (previous >>> 30)) + i) >>> 0;
      }
      // init_by_array com uma palavra de 32 bits. Isso inclui a semente zero.
      let position = 1;
      for (let remaining = 624; remaining > 0; remaining--) {
        const previous = this.state[position - 1];
        this.state[position] = ((this.state[position] ^ Math.imul(previous ^ (previous >>> 30), 1664525)) + seed) >>> 0;
        position++;
        if (position === 624) {
          this.state[0] = this.state[623];
          position = 1;
        }
      }
      for (let remaining = 623; remaining > 0; remaining--) {
        const previous = this.state[position - 1];
        this.state[position] = ((this.state[position] ^ Math.imul(previous ^ (previous >>> 30), 1566083941)) - position) >>> 0;
        position++;
        if (position === 624) {
          this.state[0] = this.state[623];
          position = 1;
        }
      }
      this.state[0] = 0x80000000;
      this.index = 624;
    }

    uint32() {
      if (this.index === 624) {
        for (let i = 0; i < 624; i++) {
          const joined = (this.state[i] & 0x80000000) | (this.state[(i + 1) % 624] & 0x7fffffff);
          this.state[i] = (this.state[(i + 397) % 624] ^ (joined >>> 1) ^ ((joined & 1) ? 0x9908b0df : 0)) >>> 0;
        }
        this.index = 0;
      }
      let value = this.state[this.index++];
      value ^= value >>> 11;
      value ^= (value << 7) & 0x9d2c5680;
      value ^= (value << 15) & 0xefc60000;
      value ^= value >>> 18;
      return value >>> 0;
    }

    stop() {
      // CPython usa getrandbits(3) e rejeita 5, 6 e 7, evitando viés de módulo.
      let value;
      do { value = this.uint32() >>> 29; } while (value >= 5);
      return value;
    }
  }

  function fromStops(stops) {
    if (!Array.isArray(stops) || stops.length !== 3 || stops.some((k) => !Number.isInteger(k) || k < 0 || k >= 5)) {
      throw new RangeError("São necessárias três paradas inteiras entre 0 e 4.");
    }
    const board = [0, 1, 2].map((row) => stops.map((k) => SYMBOLS[(k + row) % 5]));
    const center = board[1];
    const prize = center.every((symbol) => symbol === center[0]) ? PAYOUTS[center[0]] : 0;
    return { stops: [...stops], board, center, prize, profit: prize - 1 };
  }

  function spin(rng) {
    return fromStops([rng.stop(), rng.stop(), rng.stop()]);
  }

  function createSession(seed = 2026) {
    return { seed: validateSeed(seed), rng: new PythonRandom(seed), balance: INITIAL_BALANCE,
      rounds: 0, prizes: 0, wins: 0, last: null, history: [], trajectory: [INITIAL_BALANCE] };
  }

  function advance(session) {
    if (session.balance < 1 || session.rounds >= MAX_ROUNDS) {
      throw new Error("Sessão encerrada. Inicie uma nova sessão para continuar.");
    }
    const result = spin(session.rng);
    session.balance += result.profit;
    session.rounds++;
    session.prizes += result.prize;
    session.wins += Number(result.prize > 0);
    session.last = { ...result, number: session.rounds, balance: session.balance };
    session.history = [session.last, ...session.history].slice(0, 12);
    session.trajectory.push(session.balance);
    return publicState(session);
  }

  function publicState(session) {
    const { rng, ...state } = session;
    return { ...state, finished: session.balance < 1 || session.rounds >= MAX_ROUNDS,
      max_rounds: MAX_ROUNDS, initial_balance: INITIAL_BALANCE,
      rtp: session.rounds ? session.prizes / session.rounds : null };
  }

  function restore(checkpoint) {
    if (!checkpoint || checkpoint.version !== 1 || !Number.isInteger(checkpoint.rounds)
      || checkpoint.rounds < 0 || checkpoint.rounds > MAX_ROUNDS
      || typeof checkpoint.revision !== "string" || !checkpoint.revision.length || checkpoint.revision.length > 128) {
      throw new Error("O registro da sessão está incompleto ou é incompatível.");
    }
    const session = createSession(checkpoint.seed);
    // Reconstitui todos os resultados pela semente, sem confiar em saldo salvo.
    for (let i = 0; i < checkpoint.rounds; i++) advance(session);
    return session;
  }

  const api = Object.freeze({ SYMBOLS, PAYOUTS, INITIAL_BALANCE, MAX_ROUNDS,
    PythonRandom, validateSeed, fromStops, spin, createSession, advance, publicState, restore });
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.TigrifesMachine = api;
})();
