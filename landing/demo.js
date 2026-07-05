/* The Perfect Moment — interactive scrub demo.
   All frame data comes from demo-data.json (real pipeline output).
   All dynamic text is injected via textContent only — never innerHTML. */
(function () {
  "use strict";

  var STATE = { IDLE: 0, AUTOPLAY: 1, SCRUBBING: 2, SNAPPED: 3 };
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var root = document.getElementById("demo");
  if (!root) return;

  var viewerImg = document.getElementById("demo-viewer-img");
  var viewerWrap = document.getElementById("demo-viewer");
  var strip = document.getElementById("demo-strip");
  var range = document.getElementById("demo-range");
  var playhead = document.getElementById("demo-playhead");
  var panelTime = document.getElementById("demo-time");
  var panelScene = document.getElementById("demo-scene");
  var panelFinal = document.getElementById("demo-final");
  var panelReason = document.getElementById("demo-reason");
  var panelGate = document.getElementById("demo-gate");
  var duchenneChip = document.getElementById("demo-duchenne");
  var winnerStamp = document.getElementById("demo-winner-stamp");
  var replayBtn = document.getElementById("demo-replay");
  var liveRegion = document.getElementById("demo-live");

  var BAR_METRICS = [
    { key: "sharpness_norm", label: "חדות" },
    { key: "eyes_open", label: "עיניים פקוחות" },
    { key: "smile", label: "חיוך" },
    { key: "gaze", label: "מבט למצלמה" },
    { key: "composition", label: "קומפוזיציה" },
    { key: "face_lighting", label: "תאורת פנים" }
  ];

  var GATE_HEBREW = [
    { match: "eyes closed", text: "עיניים עצומות — פריים של מצמוץ לא מתחרה בכלל" },
    { match: "severe blur", text: "רך משמעותית משאר הקליפ — נפסל בשער הטשטוש" },
    { match: "closed eyes", text: "עיניים עצומות אצל חלק מהפנים בקבוצה" }
  ];

  var SCENE_HEBREW = { portrait: "דיוקן", group: "קבוצה", landscape: "ללא פנים" };

  var frames = [];
  var winnerIndex = 0;
  var current = -1;
  var state = STATE.IDLE;
  var rafId = null;
  var autoplayPos = 0;
  var inViewport = false;
  var liveTimer = null;

  function gateToHebrew(raw) {
    if (!raw) return "";
    var lower = raw.toLowerCase();
    for (var i = 0; i < GATE_HEBREW.length; i++) {
      if (lower.indexOf(GATE_HEBREW[i].match) !== -1) return GATE_HEBREW[i].text;
    }
    return raw; // fallback: raw text, still set via textContent (safe)
  }

  function metricValue(frame, key) {
    if (key === "gaze") return 1 - frame.gaze_deviation;
    if (key === "sharpness_norm") return Math.min(1, Math.sqrt(frame.sharpness / 1000));
    return frame[key];
  }

  function setFrame(i, opts) {
    i = Math.max(0, Math.min(frames.length - 1, i));
    if (i === current && !(opts && opts.force)) return;
    current = i;
    var f = frames[i];

    viewerImg.src = f.winner && f.imgHi ? f.imgHi : f.img;
    viewerImg.alt = "פריים בשנייה " + f.t.toFixed(1) + ", ציון " + f.final.toFixed(2);

    viewerWrap.classList.toggle("gated", !!f.gated);
    viewerWrap.classList.toggle("winner", !!f.winner && state === STATE.SNAPPED);

    panelTime.textContent = f.t.toFixed(1) + "s";
    panelScene.textContent = SCENE_HEBREW[f.scene] || f.scene;
    panelFinal.textContent = f.final.toFixed(3);

    if (f.gated) {
      panelGate.textContent = gateToHebrew(f.gate_reason);
      panelGate.hidden = false;
      panelReason.hidden = true;
    } else {
      panelGate.hidden = true;
      panelReason.hidden = false;
    }

    duchenneChip.hidden = !(f.duchenne_bonus > 0.2);

    for (var m = 0; m < BAR_METRICS.length; m++) {
      var metric = BAR_METRICS[m];
      var bar = document.getElementById("bar-" + metric.key);
      var val = document.getElementById("barval-" + metric.key);
      var v = Math.max(0, Math.min(1, metricValue(f, metric.key)));
      bar.style.transform = "scaleX(" + v.toFixed(3) + ")";
      bar.classList.toggle("low", v < 0.4);
      val.textContent = v.toFixed(2);
    }

    // strip highlight + playhead position (RTL: frame 0 is rightmost)
    var thumbs = strip.querySelectorAll(".demo-thumb");
    for (var t = 0; t < thumbs.length; t++) {
      thumbs[t].classList.toggle("active", t === i);
    }
    var pct = frames.length > 1 ? (i / (frames.length - 1)) * 100 : 0;
    playhead.style.insetInlineStart = pct + "%";

    range.value = String(i);
    range.setAttribute(
      "aria-valuetext",
      "פריים " + (i + 1) + " מתוך " + frames.length + ", ציון " + f.final.toFixed(2)
    );

    // debounced screen-reader announcement (announce on settle only)
    if (liveTimer) clearTimeout(liveTimer);
    liveTimer = setTimeout(function () {
      liveRegion.textContent =
        "פריים " + (i + 1) + ": ציון " + f.final.toFixed(2) + (f.gated ? ", נפסל" : "");
    }, 500);
  }

  function typewriter(el, text) {
    if (reducedMotion) {
      el.textContent = text;
      return;
    }
    el.textContent = "";
    var pos = 0;
    (function tick() {
      if (pos <= text.length && state === STATE.SNAPPED) {
        el.textContent = text.slice(0, pos);
        pos++;
        setTimeout(tick, 20);
      }
    })();
  }

  function reasonToHebrew(raw) {
    // The pipeline's reason strings are English fragments; map to Hebrew.
    var map = {
      "genuine smile": "חיוך אמיתי",
      "neutral expression": "הבעה ניטרלית",
      "weak expression": "הבעה חלשה",
      "gaze at camera": "מבט למצלמה",
      "gaze away from camera": "מבט הצידה",
      "sharp": "חד",
      "soft but above the blur gate": "רך אבל מעל שער הטשטוש"
    };
    return raw
      .split(", ")
      .map(function (part) { return map[part] || part; })
      .join(" · ");
  }

  function snapToWinner() {
    state = STATE.SNAPPED;
    var from = current;
    var steps = Math.abs(winnerIndex - from);
    if (steps === 0 || reducedMotion) {
      setFrame(winnerIndex, { force: true });
      finishSnap();
      return;
    }
    var dir = winnerIndex > from ? 1 : -1;
    var stepTime = Math.max(40, 700 / steps);
    (function step() {
      if (state !== STATE.SNAPPED) return;
      if (current !== winnerIndex) {
        setFrame(current + dir);
        setTimeout(step, stepTime);
      } else {
        finishSnap();
      }
    })();
  }

  function finishSnap() {
    viewerWrap.classList.add("winner");
    winnerStamp.hidden = false;
    replayBtn.hidden = false;
    var f = frames[winnerIndex];
    typewriter(panelReason, "הבחירה של המנוע: " + reasonToHebrew(f.reason));
  }

  function leaveSnapped() {
    winnerStamp.hidden = true;
    replayBtn.hidden = true;
    viewerWrap.classList.remove("winner");
  }

  // ---- autoplay (rAF, guarded by document.hidden + viewport visibility) ----
  function autoplayFrame() {
    rafId = null;
    if (state !== STATE.AUTOPLAY || document.hidden || !inViewport) return;
    autoplayPos += 0.012;
    if (autoplayPos >= frames.length) autoplayPos = 0;
    setFrame(Math.floor(autoplayPos));
    rafId = requestAnimationFrame(autoplayFrame);
  }

  function startAutoplay() {
    if (reducedMotion) { setFrame(winnerIndex, { force: true }); return; }
    leaveSnapped();
    state = STATE.AUTOPLAY;
    autoplayPos = current >= 0 ? current : 0;
    if (!rafId) rafId = requestAnimationFrame(autoplayFrame);
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden && state === STATE.AUTOPLAY && !rafId) {
      rafId = requestAnimationFrame(autoplayFrame);
    }
  });

  // ---- input: pointer scrubbing (RTL: rightmost = frame 0) ----
  function pointerToIndex(clientX) {
    var rect = strip.getBoundingClientRect();
    var ratio = (rect.right - clientX) / rect.width;
    return Math.round(ratio * (frames.length - 1));
  }

  strip.addEventListener("pointerdown", function (e) {
    leaveSnapped();
    state = STATE.SCRUBBING;
    strip.setPointerCapture(e.pointerId);
    setFrame(pointerToIndex(e.clientX));
    e.preventDefault();
  });
  strip.addEventListener("pointermove", function (e) {
    if (state !== STATE.SCRUBBING) return;
    setFrame(pointerToIndex(e.clientX));
  });
  strip.addEventListener("pointerup", function () {
    if (state !== STATE.SCRUBBING) return;
    snapToWinner();
  });
  strip.addEventListener("pointercancel", function () {
    if (state === STATE.SCRUBBING) snapToWinner();
  });

  // ---- input: keyboard via the real range input ----
  var keyIdleTimer = null;
  range.addEventListener("input", function () {
    leaveSnapped();
    state = STATE.SCRUBBING;
    setFrame(parseInt(range.value, 10));
    if (keyIdleTimer) clearTimeout(keyIdleTimer);
    keyIdleTimer = setTimeout(function () {
      if (state === STATE.SCRUBBING) snapToWinner();
    }, 900);
  });

  replayBtn.addEventListener("click", startAutoplay);

  // ---- boot: fetch data, build strip, warm images, observe viewport ----
  fetch("demo-data.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      frames = data.frames;
      for (var i = 0; i < frames.length; i++) {
        if (frames[i].winner) {
          winnerIndex = i;
          frames[i].imgHi = "demo/winner-hi.webp";
        }
        var thumb = document.createElement("img");
        thumb.className = "demo-thumb";
        thumb.src = frames[i].img;
        thumb.alt = "פריים " + (i + 1);
        thumb.width = 46;
        thumb.height = 82;
        thumb.decoding = "async";
        thumb.draggable = false;
        if (frames[i].gated) thumb.classList.add("gated");
        strip.appendChild(thumb);
      }
      range.max = String(frames.length - 1);
      setFrame(0, { force: true });

      var observer = new IntersectionObserver(
        function (entries) {
          inViewport = entries[0].isIntersecting;
          if (inViewport && state === STATE.IDLE) startAutoplay();
          if (inViewport && state === STATE.AUTOPLAY && !rafId) {
            rafId = requestAnimationFrame(autoplayFrame);
          }
        },
        { rootMargin: "300px" }
      );
      observer.observe(root);

      // expose a tiny debug handle for automated verification
      window.__pmDemo = {
        setFrame: setFrame,
        get index() { return current; },
        get state() { return state; },
        get rafActive() { return rafId !== null; },
        frames: frames,
        winnerIndex: winnerIndex
      };
    })
    .catch(function () {
      // demo data missing: hide the interactive shell, noscript-like fallback stays
      root.classList.add("demo-unavailable");
    });
})();
