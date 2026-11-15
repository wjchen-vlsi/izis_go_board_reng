class BoardModel {
    static POINTS = 361;
    static SIDE = 19;
    static PACING_TOLERANCE_MS = 10;
    static MAX_FRAME_CHARS = 370;
    static LONG_PRESS_MS = 1200;
    static MERGE_MS = 200;
    static PAUSE_MS = 135;
    static MIN_LATENCY_MS = 20;
    static MAX_LATENCY_MS = 50;
    static MATRIX_LATENCY_MS = 140;
    static HOT_FULL_LENGTH = 66;
    static HOT_COUNT_INDEX = 65;
    static HOT_SEGMENT = 16;
    static ICON_LEVEL = 100;
    static SEPARATOR = '0.32';
    static GARBLE_MARK = '?';
    static SIZES = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 19];
    static OFF = [0, 0, 0];
    static TOP_ON = [0, 30, 0];
    static BOTTOM_ON = [10, 10, 10];
    static FRAME_COLOR = [5, 26, 4];
    static FILL_COLOR = [15, 15, 15];
    static PALETTES = {
        SAR: {
            '1': [0, 150, 0], '2': [50, 50, 50], '3': [0, 70, 0], '4': [40, 40, 70], '5': [255, 0, 0],
            '6': [238, 20, 147], '7': [255, 110, 180], '8': [0, 80, 80], '9': [33, 33, 24],
        },
        SAL: { '1': [0, 70, 0], '2': [40, 40, 70] },
        SAM: { '1': [0, 68, 0], '2': [45, 45, 45] },
        SAW: { '1': [0, 45, 0], '2': [30, 30, 30] },
    };
    static ICONS = {
        RLT: { channel: 1, points: [129, 147, 165, 183, 201, 181, 161, 141, 121, 101, 81, 61] },
        RLW: { channel: 0, points: [90, 108, 126, 144, 162, 180, 198, 216, 234, 82, 102, 122, 142, 162, 182, 202, 222, 242] },
        RLO: { channel: 1, points: [81, 85, 89, 90, 101, 104, 107, 110, 121, 123, 125, 130, 141, 142, 144, 149, 159, 161, 163, 168, 177, 180, 183, 186, 195, 199, 203, 204] },
    };
    static SENSOR_READINGS = ['1.5', '0.4', '2.5'];
    static BUTTON_FRAMES = {
        top: { click: '~BKY#', long: '~BTK#' },
        bottom: { click: '~WKY#', long: '~WTK#' },
    };
    static SLOW_CODES = ['RGC', 'RGF', 'FLL'];
    static FULL_MATRIX_RE = /^~?SA[RLMW]\d{361}#?$/;
    static LOSS_AFTER_SHORT = [[0, 1], [10, 0.8], [20, 0.5], [30, 0.1], [40, 0]];
    static LOSS_AFTER_MATRIX = [[0, 1], [30, 1], [40, 0.9], [50, 0.9], [60, 0.8], [70, 0.5], [80, 0.3], [90, 0]];
    static DANGER_PREFIXES = ['UPD', 'ADJ', 'SEP', 'WBS', 'CRCYES', 'CRCERR', 'CRY', 'CRE'];

    static number(text) {
        const match = text.match(/^\d+/);
        return match ? parseInt(match[0], 10) : 0;
    }

    static colorAt(text, start) {
        return [0, 4, 8].map((step) => Math.min(255, BoardModel.number(text.slice(start + step, start + step + 3))));
    }

    static interpolate(points, x) {
        if (x <= points[0][0]) return points[0][1];
        for (let i = 1; i < points.length; i++) {
            const [x1, y1] = points[i];
            if (x > x1) continue;
            const [x0, y0] = points[i - 1];
            return y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
        }
        return points[points.length - 1][1];
    }

    static outcome(fields = {}) {
        return { replies: [], lost: false, ignored: false, warning: null, danger: null, ...fields };
    }

    static dangerOf(text) {
        const prefix = BoardModel.DANGER_PREFIXES.find((candidate) => text.startsWith(candidate));
        if (prefix === undefined) return null;
        return `[DANGER] ~${prefix} is a command of specification section 3.8: on the board it changes the settings memory permanently or belongs to a firmware update. The simulator ignores it: no reply, no effect.`;
    }

    constructor({ random = Math.random, calibrationMs = 16000 } = {}) {
        this.random = random;
        this.calibrationMs = calibrationMs;
        this.options = { frameLoss: false, garbleNext: false };
        this.state = { stones: new Array(BoardModel.POINTS).fill(0), beeps: 0 };
        this.restart(true);
    }

    restart(autoReport) {
        const state = this.state;
        state.size = BoardModel.SIDE;
        state.autoReport = autoReport;
        state.leds = Array.from({ length: BoardModel.POINTS }, () => [...BoardModel.OFF]);
        state.top = [...BoardModel.OFF];
        state.bottom = [...BoardModel.OFF];
        this.frameCells = new Array(BoardModel.POINTS).fill(false);
        this.pointSlot = null;
        this.lastHot = null;
        this.pending = [];
        this.lastRelease = {};
        this.downAt = {};
        this.merged = {};
        this.pausedUntil = -Infinity;
        this.reportDue = false;
        this.lastFrameAt = null;
        this.lastCode = '';
        this.lastFull = false;
        this.readyAt = -Infinity;
        this.announcePending = false;
    }

    powerCycle(atMs) {
        this.restart(true);
        this.readyAt = atMs + this.calibrationMs;
        this.announcePending = true;
        return this.tick(atMs);
    }

    receive(frame, atMs) {
        const match = frame.match(/^~?([A-Z]{3})([^~#]*)#?$/);
        if (!match) return BoardModel.outcome();
        const code = match[1];
        const danger = BoardModel.dangerOf(code + match[2]);
        if (atMs < this.readyAt) return BoardModel.outcome({ ignored: true, danger });
        const lost = this.dropsFrame(atMs);
        const warning = this.checkDelay(code, frame, atMs);
        if (lost) return BoardModel.outcome({ lost: true, warning, danger });
        const length = frame.endsWith('#') ? frame.length - 1 : frame.length;
        const silent = danger !== null || length > BoardModel.MAX_FRAME_CHARS;
        const replies = silent ? [] : this.execute(code, match[2], atMs);
        return BoardModel.outcome({ replies, warning, danger });
    }

    setStone(index, color, atMs) {
        if (!Number.isInteger(index) || index < 0 || index >= BoardModel.POINTS) return [];
        if (this.state.stones[index] === color) return [];
        this.state.stones[index] = color;
        return this.report(atMs);
    }

    clearStones(atMs) {
        if (!this.state.stones.some((stone) => stone !== 0)) return [];
        this.state.stones.fill(0);
        return this.report(atMs);
    }

    buttonDown(button, atMs) {
        if (atMs < this.readyAt) return [];
        if (!BoardModel.BUTTON_FRAMES[button] || this.downAt[button] !== undefined) return [];
        this.downAt[button] = atMs;
        const lastUp = this.lastRelease[button];
        if (lastUp !== undefined && atMs - lastUp < BoardModel.MERGE_MS) {
            this.pending = this.pending.filter((item) => item.button !== button);
            delete this.lastRelease[button];
            this.merged[button] = true;
        }
        return this.tick(atMs);
    }

    buttonUp(button, atMs) {
        const frames = BoardModel.BUTTON_FRAMES[button];
        const downMs = this.downAt[button];
        if (!frames || downMs === undefined) return [];
        delete this.downAt[button];
        if (this.merged[button]) {
            delete this.merged[button];
            return [frames.click];
        }
        this.lastRelease[button] = atMs;
        const held = atMs - downMs >= BoardModel.LONG_PRESS_MS;
        this.pending.push({ at: atMs + BoardModel.MERGE_MS, frame: held ? frames.long : frames.click, button });
        return [];
    }

    pressButton(button, downMs, upMs) {
        return [...this.buttonDown(button, downMs), ...this.buttonUp(button, upMs)];
    }

    tick(atMs) {
        const due = this.pending.filter((item) => item.at <= atMs).sort((a, b) => a.at - b.at);
        this.pending = this.pending.filter((item) => item.at > atMs);
        const frames = due.map((item) => item.frame);
        if (this.announcePending && atMs >= this.readyAt) {
            this.announcePending = false;
            frames.push('~GBS19#', this.sda());
        }
        if (this.reportDue && atMs >= this.pausedUntil) {
            this.reportDue = false;
            if (this.state.autoReport) frames.push(this.sda());
        }
        return frames;
    }

    latency(frame) {
        if (BoardModel.FULL_MATRIX_RE.test(frame)) return BoardModel.MATRIX_LATENCY_MS;
        const span = BoardModel.MAX_LATENCY_MS - BoardModel.MIN_LATENCY_MS;
        return Math.round(BoardModel.MIN_LATENCY_MS + this.random() * span);
    }

    report(atMs) {
        if (!this.state.autoReport || atMs < this.readyAt) return [];
        if (atMs < this.pausedUntil) {
            this.reportDue = true;
            return [];
        }
        this.reportDue = false;
        return [this.sda()];
    }

    pauseReports(atMs) {
        this.pausedUntil = atMs + BoardModel.PAUSE_MS;
    }

    sda() {
        const size = this.state.size;
        let digits = '';
        for (let i = 0; i < size * size; i++) digits += this.state.stones[this.physicalIndex(i)];
        if (this.options.garbleNext) {
            this.options.garbleNext = false;
            digits = digits.slice(0, -1) + BoardModel.GARBLE_MARK;
        }
        return `~SDA${digits}#`;
    }

    readings() {
        const entries = this.state.stones.map((stone, i) => {
            const volts = BoardModel.SENSOR_READINGS[stone];
            return `${i + 1}b${volts}w${volts}`;
        });
        return `~DAT${entries.join(',')}#`;
    }

    physicalIndex(logicalIndex) {
        const size = this.state.size;
        if (size === BoardModel.SIDE) return logicalIndex;
        const offset = Math.floor((BoardModel.SIDE - size) / 2);
        const row = Math.floor(logicalIndex / size);
        const column = logicalIndex % size;
        return (row + offset) * BoardModel.SIDE + (column + offset);
    }

    physicalOf(position) {
        const logical = position - 1;
        if (!(logical >= 0)) return null;
        const size = this.state.size;
        const offset = Math.floor((BoardModel.SIDE - size) / 2);
        const row = Math.floor(logical / size) + offset;
        const column = (logical % size) + offset;
        return row < BoardModel.SIDE ? row * BoardModel.SIDE + column : null;
    }

    logicalOf(physical) {
        const size = this.state.size;
        const offset = Math.floor((BoardModel.SIDE - size) / 2);
        const row = Math.floor(physical / BoardModel.SIDE) - offset;
        const column = (physical % BoardModel.SIDE) - offset;
        if (!(physical >= 0) || row < 0 || row >= size || column < 0 || column >= size) return null;
        return row * size + column + 1;
    }

    screenOrigin() {
        const size = this.state.size;
        const offset = Math.floor((BoardModel.SIDE - size) / 2);
        return { row: offset, column: BoardModel.SIDE - offset - size };
    }

    dropsFrame(atMs) {
        if (!this.options.frameLoss || this.lastFrameAt === null) return false;
        const table = this.lastFull ? BoardModel.LOSS_AFTER_MATRIX : BoardModel.LOSS_AFTER_SHORT;
        const probability = BoardModel.interpolate(table, atMs - this.lastFrameAt);
        return probability > 0 && this.random() < probability;
    }

    checkDelay(code, frame, atMs) {
        let warning = null;
        if (this.lastFrameAt !== null) {
            const required = BoardModel.SLOW_CODES.includes(this.lastCode) ? 240 : 80;
            const elapsed = atMs - this.lastFrameAt;
            if (elapsed < required - BoardModel.PACING_TOLERANCE_MS) {
                warning = `⚠️ [Delay Warning] Only ${elapsed}ms elapsed since last command (${this.lastCode}). Expected >= ${required}ms.`;
            }
        }
        this.lastFrameAt = atMs;
        this.lastCode = code;
        this.lastFull = BoardModel.FULL_MATRIX_RE.test(frame);
        return warning;
    }

    execute(code, payload, atMs) {
        const state = this.state;
        const replies = [];
        switch (code) {
            case 'STA': replies.push(this.sda()); break;
            case 'GVE': replies.push('~VER121#'); break;
            case 'GSV': replies.push(`~FJX${BoardModel.SEPARATOR}#`); break;
            case 'GBS': replies.push('~BHZ255#'); break;
            case 'REQ': replies.push(this.readings()); break;
            case 'CTS': state.autoReport = payload === '1'; replies.push(`~UDS${payload}#`); break;
            case 'RGC': this.fillLeds(() => BoardModel.OFF, () => true); replies.push('~ALC#'); break;
            case 'RGF': this.fillLeds(() => BoardModel.OFF, (i) => !this.frameCells[i]); replies.push('~SIC#'); break;
            case 'FLL': this.fillLeds(() => BoardModel.FILL_COLOR, () => true); break;
            case 'LED': this.executeLed(payload, replies); break;
            case 'GLC': this.executeGlc(payload, replies); break;
            case 'SHP': case 'TLO': this.executePoint(code, payload, replies); break;
            case 'HOT': this.executeHot(payload, replies); break;
            case 'SAR': case 'SAL': case 'SAM': case 'SAW': this.executeMatrix(code, payload, atMs, replies); break;
            case 'BOD': case 'BSC': this.executeBoundary(code, payload, atMs, replies); break;
            case 'AWO': state.beeps += 1; this.pauseReports(atMs); break;
            case 'RLT': case 'RLW': case 'RLO': this.drawIcon(code); this.pauseReports(atMs); replies.push('~DSC#'); break;
            default: break;
        }
        return replies;
    }

    fillLeds(colorOf, selected) {
        for (let i = 0; i < BoardModel.POINTS; i++) {
            if (selected(i)) this.state.leds[i] = [...colorOf(i)];
        }
    }

    applyTurn(mode) {
        const state = this.state;
        if (mode === '0') { state.top = [...BoardModel.OFF]; state.bottom = [...BoardModel.OFF]; }
        else if (mode === '1') { state.top = [...BoardModel.TOP_ON]; state.bottom = [...BoardModel.OFF]; }
        else if (mode === '2') { state.top = [...BoardModel.OFF]; state.bottom = [...BoardModel.BOTTOM_ON]; }
        else if (mode === '3') { state.top = [...BoardModel.TOP_ON]; state.bottom = [...BoardModel.BOTTOM_ON]; }
    }

    executeLed(payload, replies) {
        if (payload === '11') this.applyTurn('1');
        else if (payload === '21') this.applyTurn('2');
        else if (payload === '10' || payload === '20') this.applyTurn('0');
        replies.push('~LOS#');
    }

    executeGlc(payload, replies) {
        const color = BoardModel.colorAt(payload, 2);
        if (payload[0] === '1') this.state.top = color;
        else if (payload[0] === '2') this.state.bottom = color;
        replies.push('~LOS#');
    }

    switchOffPoint() {
        if (this.pointSlot === null) return;
        this.state.leds[this.pointSlot] = [...BoardModel.OFF];
        this.pointSlot = null;
    }

    executePoint(code, payload, replies) {
        this.switchOffPoint();
        if (!payload.includes(',')) return;
        const physical = this.physicalOf(BoardModel.number(payload));
        if (physical !== null) {
            this.state.leds[physical] = BoardModel.colorAt(payload, 5);
            this.pointSlot = physical;
        }
        if (code === 'TLO') {
            this.applyTurn(payload[17] ?? '0');
            replies.push('~TLS#');
        } else {
            replies.push('~HCS#');
        }
    }

    executeHot(payload, replies) {
        let frame = payload;
        if (payload.length < BoardModel.HOT_FULL_LENGTH) frame = this.lastHot;
        else this.lastHot = payload;
        if (frame !== null) this.drawHot(frame);
        replies.push('~HSM#');
    }

    drawHot(payload) {
        const count = BoardModel.number(payload.slice(BoardModel.HOT_COUNT_INDEX, BoardModel.HOT_COUNT_INDEX + 1));
        for (let i = 0; i < Math.min(count, 4); i++) {
            const base = i * BoardModel.HOT_SEGMENT;
            const physical = this.physicalOf(BoardModel.number(payload.slice(base + 1, base + 4)));
            if (physical !== null) this.state.leds[physical] = BoardModel.colorAt(payload, base + 5);
        }
    }

    executeMatrix(code, payload, atMs, replies) {
        if (!/^\d{361}$/.test(payload)) return;
        const palette = BoardModel.PALETTES[code];
        for (let i = 0; i < BoardModel.POINTS; i++) {
            const digit = payload[i];
            if (digit === '0') this.state.leds[i] = [...BoardModel.OFF];
            else if (palette[digit]) this.state.leds[i] = [...palette[digit]];
        }
        this.pauseReports(atMs);
        replies.push('~ALS#');
    }

    eraseFrame() {
        for (let i = 0; i < BoardModel.POINTS; i++) {
            if (!this.frameCells[i]) continue;
            this.frameCells[i] = false;
            this.state.leds[i] = [...BoardModel.OFF];
        }
    }

    drawFrame(size, color) {
        if (size === BoardModel.SIDE) return;
        const offset = Math.floor((BoardModel.SIDE - size) / 2);
        for (let r = -1; r <= size; r++) {
            for (let c = -1; c <= size; c++) {
                if (r !== -1 && r !== size && c !== -1 && c !== size) continue;
                const physical = (r + offset) * BoardModel.SIDE + (c + offset);
                this.state.leds[physical] = [...color];
                this.frameCells[physical] = true;
            }
        }
    }

    executeBoundary(code, payload, atMs, replies) {
        const text = payload.slice(0, 2);
        const size = /^\d\d$/.test(text) ? parseInt(text, 10) : 0;
        const shaped = code === 'BSC' || payload.length === 2;
        if (!shaped || !BoardModel.SIZES.includes(size)) {
            this.state.size = BoardModel.SIDE;
            this.frameCells.fill(false);
            return;
        }
        this.eraseFrame();
        this.state.size = size;
        this.drawFrame(size, code === 'BSC' ? BoardModel.colorAt(payload, 3) : BoardModel.FRAME_COLOR);
        replies.push(`~GBS${text}#`);
        if (code === 'BSC' || size !== BoardModel.SIDE) this.pauseReports(atMs);
    }

    drawIcon(code) {
        const { channel, points } = BoardModel.ICONS[code];
        for (const point of points) {
            const color = [...this.state.leds[point - 1]];
            color[channel] = BoardModel.ICON_LEVEL;
            this.state.leds[point - 1] = color;
        }
    }
}
