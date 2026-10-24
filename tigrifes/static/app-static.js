"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const spinButton = $("spin-button");
  const message = $("result-message");
  const board = $("board");
  const symbols = JSON.parse(board.getAttribute("data-symbols"));
  const dialog = $("reset-dialog");
  const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
  // Cada instalação em github.io tem seu próprio espaço de armazenamento.
  const key = `tigrifes:session:v1:${new URL("../", document.currentScript.src).pathname}`;
  let storage;
  try { storage = globalThis.localStorage; } catch (_) { storage = null; }
  const store = new globalThis.TigrifesSessions.SessionStore(storage, key);
  let current = null;
  let busy = false;
  let resetRevision = null;
  let pendingSync = false;

  function signed(value) { return `${value > 0 ? "+" : ""}${number.format(value)}`; }
  function emojiLine(line) { return line.map((symbol) => symbols[symbol].emoji).join(" · "); }
  function namedLine(line) { return line.map((symbol) => symbols[symbol].name).join(", "); }

  function setBusy(value) {
    busy = value;
    spinButton.disabled = value || !current || current.state.finished;
    spinButton.classList.toggle("finished", Boolean(current?.state.finished));
    $("open-reset").disabled = value || !current;
    $("reset-submit").disabled = value;
    $("close-reset").disabled = value;
    board.classList.toggle("is-spinning", value && !dialog.open);
    board.setAttribute("aria-busy", String(value));
  }

  function render(envelope, announce = false) {
    current = envelope;
    const state = envelope.state;
    $("balance").textContent = number.format(state.balance);
    $("session-profit").textContent = signed(state.balance - state.initial_balance);
    $("round-count").textContent = state.rounds;
    $("win-count").textContent = state.wins;
    $("round-label").textContent = `RODADA ${state.rounds} / ${state.max_rounds}`;
    $("seed-label").textContent = state.seed;
    $("observed-rtp").textContent = state.rtp === null ? "—" : `${number.format(state.rtp * 100)}%`;
    $("session-storage-note").textContent = store.persistent
      ? "Saldo e histórico salvos somente neste navegador. Limpar os dados do site apaga a sessão."
      : "O navegador bloqueou o armazenamento. Você pode jogar, mas a sessão será perdida ao fechar ou recarregar esta página.";
    const values = state.last?.board || [["A", "C", "E"], ["B", "D", "A"], ["C", "E", "B"]];
    board.querySelectorAll(".symbol").forEach((cell, i) => {
      const symbol = values[Math.floor(i / 3)][i % 3];
      cell.textContent = symbols[symbol].emoji;
      cell.className = `symbol symbol-${symbol}`;
    });
    board.setAttribute("aria-label", state.last
      ? `Rodada ${state.rounds}. Topo: ${namedLine(values[0])}. Linha central válida: ${namedLine(values[1])}. Base: ${namedLine(values[2])}.`
      : "Tabuleiro ilustrativo, ainda sem sorteio. Apenas a linha central gera prêmio.");
    const history = $("history-body");
    history.replaceChildren();
    if (!state.history.length) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 5;
      td.className = "empty-state";
      td.textContent = "Seus resultados aparecem aqui depois do primeiro giro.";
      tr.append(td);
      history.append(tr);
    }
    state.history.forEach((round) => {
      const tr = document.createElement("tr");
      [String(round.number).padStart(2, "0"), emojiLine(round.center), `${round.prize} cr.`, `${signed(round.profit)} cr.`, `${round.balance} cr.`].forEach((value, i) => {
        const cell = document.createElement(i === 0 ? "th" : "td");
        if (i === 0) cell.scope = "row";
        if (i === 1) {
          cell.className = "history-symbols";
          cell.setAttribute("aria-label", namedLine(round.center));
        }
        if (i === 3) cell.className = `history-profit ${round.profit > 0 ? "positive" : "negative"}`;
        cell.textContent = value;
        tr.append(cell);
      });
      history.append(tr);
    });
    const balances = state.trajectory;
    const minimum = Math.min(...balances);
    const maximum = Math.max(...balances);
    const min = minimum - 5;
    const max = maximum + 5;
    const points = balances.length === 1 ? "0,38 320,38" : balances.map((b, i) => `${i / (balances.length - 1) * 320},${70 - (b - min) / (max - min) * 64}`).join(" ");
    const baseline = 70 - (100 - min) / (max - min) * 64;
    $("balance-line").setAttribute("points", points);
    $("balance-chart").querySelector(".chart-baseline").setAttribute("d", `M0 ${baseline}H320`);
    $("balance-chart").setAttribute("aria-label", `Saldo em ${state.rounds} rodadas: início 100, mínimo ${minimum}, máximo ${maximum}, atual ${state.balance} créditos.`);
    message.classList.toggle("has-prize", Boolean(state.last?.prize));
    if (state.finished) {
      message.textContent = state.balance < 1
        ? "Sessão encerrada: os créditos se esgotaram. Você pode iniciar outra sessão."
        : "500 rodadas concluídas. Explore o histórico ou inicie uma nova sessão.";
    } else if (state.last) {
      message.textContent = `Rodada ${state.rounds}: ${emojiLine(state.last.center)}. Prêmio ${state.last.prize} cr. · Lucro ${signed(state.last.profit)} cr.${announce ? ` Saldo: ${state.balance}.` : ""}`;
    } else {
      message.textContent = "Tudo pronto. Cada rodada é um novo sorteio.";
    }
    setBusy(busy);
  }

  function exclusive(operation) {
    // Web Locks serializa as alterações entre abas em HTTPS/localhost.
    // No fallback, a revisão e o evento storage detectam alterações concorrentes.
    return globalThis.navigator?.locks?.request
      ? navigator.locks.request(key, operation)
      : Promise.resolve().then(operation);
  }

  function synchronize() {
    render(store.load());
    pendingSync = false;
  }

  spinButton.addEventListener("click", async () => {
    if (busy || !current || current.state.finished) return;
    const expected = current.checkpoint.revision;
    setBusy(true);
    message.textContent = "Sorteando três paradas independentes…";
    try {
      const [result] = await Promise.all([
        exclusive(() => store.spin(expected)),
        new Promise((resolve) => setTimeout(resolve, matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 440))
      ]);
      render(result, true);
    } catch (error) {
      synchronize();
      message.textContent = error.message;
    } finally {
      setBusy(false);
      if (pendingSync) synchronize();
    }
  });

  $("open-reset").addEventListener("click", () => {
    $("seed-input").value = current.state.seed;
    $("reset-error").textContent = "";
    resetRevision = current.checkpoint.revision;
    dialog.showModal();
    $("seed-input").focus();
  });
  $("close-reset").addEventListener("click", () => dialog.close());
  dialog.addEventListener("cancel", (event) => { if (busy) event.preventDefault(); });
  $("reset-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    $("reset-error").textContent = "";
    try {
      const seed = Number($("seed-input").value);
      render(await exclusive(() => store.reset(seed, resetRevision)));
      dialog.close();
    } catch (error) {
      synchronize();
      resetRevision = current.checkpoint.revision;
      $("reset-error").textContent = error.message;
    } finally {
      setBusy(false);
      if (pendingSync) synchronize();
      if (!dialog.open) spinButton.focus();
    }
  });

  globalThis.addEventListener("storage", (event) => {
    if (!store.persistent || (event.key !== key && event.key !== null)) return;
    if (busy) pendingSync = true;
    else synchronize();
  });

  synchronize();
  if (store.recovered) {
    message.textContent = "O registro anterior não pôde ser restaurado. Uma nova sessão com 100 créditos foi iniciada.";
  }
})();
