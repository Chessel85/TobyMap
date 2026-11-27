// Talking to the worker, one message at a time (architecture 5.7).
// If movement keys arrive faster than the worker answers, the waiting
// movements are joined into one message. The core carries out every one of
// them and speaks only the last, so no step is lost and speech never falls
// behind (ANN-3).

export class WorkerClient {
  constructor(url) {
    this.worker = new Worker(url, { type: "module" });
    this.worker.onmessage = (e) => this._answer(e.data);
    this.worker.onerror = (e) => this._fail(e.message || "The worker could not start.");
    this.queue = [];
    this.inFlight = null;
    this.nextId = 1;
    this.latestOnly = new Set();
    this.waiting = new Map();   // background work, by type, sent only when nothing else is waiting (P2-T5, P3-T24a)
    this.onNotice = () => {};   // progress messages from the worker, such as the map download
    this.onUpdate = () => {};   // the core's answers the worker sends of its own, such as a download that went wrong
  }

  send(message) {
    return new Promise((resolve, reject) => {
      const last = this.queue[this.queue.length - 1];
      if (last && this._isMovement(message) && this._isMovement(last.message)) {
        // Join it to the waiting movements; the earlier caller gets null.
        last.message.commands.push(...message.commands);
        last.message.width = message.width;
        last.message.height = message.height;
        last.resolve(null);
        last.resolve = resolve;
        last.reject = reject;
        return;
      }
      this.queue.push({ message: { ...message, id: this.nextId++ }, resolve, reject });
      this._pump();
    });
  }

  // Background work, such as the Crossed and passed search and the drawing's steps: sent when
  // the worker has nothing else to do, so a key press never waits for it. A newer one of the
  // same type replaces one not yet sent.
  idle(message) {
    return new Promise((resolve, reject) => {
      const old = this.waiting.get(message.type);
      if (old) old.resolve(null);
      this.waiting.delete(message.type);
      this.waiting.set(message.type, { message, resolve, reject });
      this._pump();
    });
  }

  _isMovement(message) {
    return message.type === "run" && message.commands.every(([name]) => this.latestOnly.has(name));
  }

  _pump() {
    if (this.inFlight) return;
    if (!this.queue.length && this.waiting.size) {
      const [type, next] = this.waiting.entries().next().value;
      this.waiting.delete(type);
      this.queue.push({ ...next, message: { ...next.message, id: this.nextId++ } });
    }
    if (!this.queue.length) return;
    this.inFlight = this.queue.shift();
    this.worker.postMessage(this.inFlight.message);
  }

  _answer(data) {
    if (data.notice !== undefined) { this.onNotice(data.notice); return; }
    if (data.update !== undefined) { this.onUpdate(data.update); return; }   // an answer nothing asked for (P4-T6c)
    const entry = this.inFlight;
    this.inFlight = null;
    if (entry) {
      if (data.ok) entry.resolve(data.result);
      else entry.reject(new Error(data.error));
    }
    this._pump();
  }

  _fail(message) {
    const all = [this.inFlight, ...this.queue, ...this.waiting.values()].filter(Boolean);
    this.waiting = new Map();
    this.inFlight = null;
    this.queue = [];
    for (const entry of all) entry.reject(new Error(message));
  }
}
