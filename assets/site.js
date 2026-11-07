(function () {
  var root = document.documentElement;
  var toggle = document.querySelector("[data-theme-toggle]");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var dark = root.dataset.theme
        ? root.dataset.theme === "dark"
        : window.matchMedia("(prefers-color-scheme: dark)").matches;
      var next = dark ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("onedpi-theme", next); } catch (e) {}
    });
  }

  var demo = document.querySelector("[data-demo]");
  if (!demo) return;

  var host = "youtube.com";
  var cases = {
    plain: {
      packets: [{ pre: "мне на", host: host, post: "" }],
      verdict: "Заблокировано",
      kind: "block",
      explain: "Адрес сайта лежит в одном пакете целиком. Фильтр видит его и рвёт соединение."
    },
    split: {
      packets: [
        { pre: "мне на", host: "you", post: "" },
        { pre: "", host: "tube.com", post: "", late: true }
      ],
      verdict: "Пропущено",
      kind: "pass",
      explain: "Адрес разрезан на два пакета, второй идёт позже. Фильтр видит обрывки и не узнаёт сайт, а сайт собирает их обратно."
    },
    ip: {
      packets: [{ pre: "мне на сервер", host: "149.154.167.51", post: "", addrOnly: true }],
      verdict: "Не доходит",
      kind: "block",
      explain: "Здесь блокируют сам адрес сервера. Пакеты не доходят ни в каком виде, поэтому нарезка не поможет. Нужен внешний сервер, то есть VPN."
    }
  };

  var packetsEl = demo.querySelector("[data-packets]");
  var verdictEl = demo.querySelector("[data-verdict]");
  var explainEl = demo.querySelector("[data-explain]");
  var tabs = demo.querySelectorAll("[data-case]");

  function cell(text, cls) {
    var b = document.createElement("b");
    b.textContent = text;
    if (cls) b.className = cls;
    return b;
  }

  function render(name) {
    var c = cases[name];
    packetsEl.textContent = "";
    c.packets.forEach(function (p) {
      var el = document.createElement("span");
      el.className = "packet" + (p.late ? " late" : "");
      if (p.pre) el.appendChild(cell(p.pre));
      if (p.addrOnly) {
        el.appendChild(cell(p.host, "addr"));
      } else {
        p.host.split("").forEach(function (ch) { el.appendChild(cell(ch, "addr")); });
      }
      packetsEl.appendChild(el);
    });
    verdictEl.textContent = c.verdict;
    verdictEl.className = "verdict " + c.kind;
    explainEl.textContent = c.explain;
    tabs.forEach(function (t) { t.setAttribute("aria-selected", t.dataset.case === name ? "true" : "false"); });
  }

  tabs.forEach(function (t) {
    t.addEventListener("click", function () { render(t.dataset.case); });
    t.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      var list = Array.prototype.slice.call(tabs);
      var i = list.indexOf(t) + (e.key === "ArrowRight" ? 1 : -1);
      var next = list[(i + list.length) % list.length];
      next.focus();
      render(next.dataset.case);
    });
  });

  render("plain");
})();
