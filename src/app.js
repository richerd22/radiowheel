(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var all = function (sel, root) { return [].slice.call((root || document).querySelectorAll(sel)); };
  var norm = function (s) { return (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase(); };
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  function readJSON(id) { try { return JSON.parse($(id).textContent); } catch (e) { return null; } }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  /* theme: follows the system until the viewer flips it */
  var tb = $("theme-btn"), root = document.documentElement;
  function isDark() { var t = root.dataset.theme; return t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches; }
  function label() { if (tb) tb.textContent = isDark() ? "Day" : "Night"; }
  if (tb) { label(); tb.addEventListener("click", function () { var n = isDark() ? "light" : "dark"; root.dataset.theme = n; store("rw-theme", n); label(); }); }

  /* reading progress */
  var pr = $("progress");
  if (pr) window.addEventListener("scroll", function () {
    var h = document.documentElement, max = h.scrollHeight - h.clientHeight;
    pr.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + "%";
  }, { passive: true });

  /* footnotes show their source on hover */
  all("sup.fn a").forEach(function (a) { var li = $("src-" + a.dataset.n); if (li) a.title = li.textContent.trim(); });

  /* search + chip filter for any list */
  function filter(input, chipsSel, items, chipAttr) {
    var q = input ? $(input) : null, k = "", chips = all(chipsSel);
    function go() {
      var t = norm(q ? q.value.trim() : "");
      items.forEach(function (el) {
        var m = (!t || norm(el.dataset.s || el.textContent).indexOf(t) > -1) && (!k || el.dataset[chipAttr] === k);
        el.classList.toggle("hide", !m);
      });
    }
    chips.forEach(function (b) { b.addEventListener("click", function () { k = b.dataset[chipAttr]; chips.forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); }); go(); }); });
    if (q) q.addEventListener("input", go);
  }
  [["gl-q", "#glossary .chips button", "#gl-list li", "x"], [null, "#timeline .chips button", "#tl-list li", "era"],
   ["tk-q", "#talk .chips button", "#tk-list li", "g"], ["hs-q", "#hosts .chips button", "#hs-list tr", "g"],
   ["lo-q", "#lore .chips button", "#lo-list li", "k"], ["cl-q", "#catalog .chips button", "#cl-list tr", "k"],
   [null, "#tracker .chips button", "#six-list li", "k"], [null, "#removed .chips button", "#rm-list tr", "g"]].forEach(function (f) {
    var items = all(f[2]); if (items.length) filter(f[0], f[1], items, f[3]);
  });

  /* the radio wheel: game tabs, and hover or focus tunes the readout */
  var tabs = all(".gt"), needle = document.querySelector(".tuner .needle");
  function showGame(g) {
    tabs.forEach(function (t) { t.setAttribute("aria-pressed", t.dataset.game === g ? "true" : "false"); });
    all(".wheel").forEach(function (w) { w.hidden = w.dataset.game !== g; });
    if (needle) { var i = tabs.map(function (t) { return t.dataset.game; }).indexOf(g); needle.style.left = (6 + (i / Math.max(1, tabs.length - 1)) * 88) + "%"; }
    store("rw-game", g);
  }
  tabs.forEach(function (t) { t.addEventListener("click", function () { showGame(t.dataset.game); }); });
  var saved = store("rw-game"); if (saved && tabs.some(function (t) { return t.dataset.game === saved; })) showGame(saved); else if (tabs.length) showGame((tabs.filter(function (t) { return t.getAttribute("aria-pressed") === "true"; })[0] || tabs[0]).dataset.game);
  all(".wheel").forEach(function (w) {
    var lcd = w.querySelector(".lcd"), def = lcd ? lcd.innerHTML : "";
    function tune(a) {
      all(".wedge", w).forEach(function (x) { x.classList.toggle("on", x === a); });
      if (!a) { lcd.innerHTML = def; return; }
      var d = {}; try { d = JSON.parse(a.getAttribute("data-info")); } catch (e) {}
      lcd.innerHTML = '<span class="l1">' + esc(d.n) + '</span><span class="l2">' + esc(d.g) + "</span>" + '<span class="l3">' + esc(d.h || (d.c ? d.c + " songs" : "")) + "</span>";
    }
    all(".wedge", w).forEach(function (a) {
      a.addEventListener("mouseenter", function () { tune(a); });
      a.addEventListener("focus", function () { tune(a); });
    });
    w.addEventListener("mouseleave", function () { tune(null); });
  });

  /* song finder: loads every song once, then filters as you type */
  var sq = $("sf-q");
  if (sq) {
    var data = null, gk = "", rmOnly = false, limit = 150, list = $("sf-list"), cnt = $("sf-cnt"), more = $("sf-more");
    var GN = {}; all("#songs .chips button").forEach(function (b) { if (b.dataset.g) GN[b.dataset.g] = b.textContent; });
    function render() {
      if (!data) return;
      var t = norm(sq.value.trim()), out = [], n = 0;
      for (var i = 0; i < data.length; i++) {
        var r = data[i];
        if (gk && r[3] !== gk) continue;
        if (rmOnly && !r[5]) continue;
        if (t && norm(r[0] + " " + r[1] + " " + r[2]).indexOf(t) < 0) continue;
        n++;
        if (out.length < limit) out.push("<tr" + (r[5] ? ' class="rm"' : "") + "><td>" + esc(r[0]) + "</td><td>" + esc(r[1]) + (r[5] ? ' <span class="tag rmt">pulled ' + esc(r[5]) + "</span>" : "") + '</td><td><a href="/stations/' + esc(r[4]) + '/">' + esc(r[2]) + '</a></td><td class="k">' + esc(GN[r[3]] || r[3]) + "</td></tr>");
      }
      list.innerHTML = out.join("");
      cnt.textContent = n.toLocaleString() + " songs";
      more.hidden = n <= limit;
    }
    fetch("/tracks-min.json").then(function (r) { return r.json(); }).then(function (d) { data = d; render(); }).catch(function () { cnt.textContent = "Could not load the song list. Try reloading."; });
    var tmr; sq.addEventListener("input", function () { clearTimeout(tmr); limit = 150; tmr = setTimeout(render, 80); });
    all("#songs .chips button").forEach(function (b) { b.addEventListener("click", function () { gk = b.dataset.g; limit = 150; all("#songs .chips button").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); }); render(); }); });
    var rm = $("sf-rm"); if (rm) rm.addEventListener("change", function () { rmOnly = rm.checked; limit = 150; render(); });
    var mb = $("sf-btn"); if (mb) mb.addEventListener("click", function () { limit += 300; render(); });
    var p = new URLSearchParams(location.search).get("q"); if (p) sq.value = p;
  }

  /* quiz */
  var qd = readJSON("quiz-data"), qz = $("quiz");
  if (qd && qz) {
    var score = 0, done = 0;
    qd.forEach(function (q, i) {
      var d = document.createElement("div"); d.className = "q";
      d.innerHTML = "<p><b>" + (i + 1) + ".</b> " + esc(q.q) + "</p>";
      q.options.forEach(function (o, j) {
        var b = document.createElement("button"); b.type = "button"; b.textContent = o;
        b.addEventListener("click", function () {
          if (d.dataset.done) return; d.dataset.done = 1; done++;
          if (j === q.answer) { score++; b.classList.add("right"); } else { b.classList.add("wrong"); d.querySelectorAll("button")[q.answer].classList.add("right"); }
          var w = document.createElement("p"); w.className = "why";
          w.innerHTML = esc(q.why) + (q.section ? ' <a href="/' + esc(q.section) + '/">Read more</a>' : "") + (done === qd.length ? " <b>Score: " + score + " of " + qd.length + ".</b>" : "");
          d.appendChild(w);
        });
        d.appendChild(b);
      });
      qz.appendChild(d);
    });
  }
})();
