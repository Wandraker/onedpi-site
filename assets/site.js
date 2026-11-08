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

  var drawer = document.getElementById("drawer");
  var opener = document.querySelector("[data-menu-open]");
  if (drawer && opener && typeof drawer.showModal === "function") {
    opener.setAttribute("aria-expanded", "false");
    opener.addEventListener("click", function () {
      drawer.showModal();
      document.body.classList.add("drawer-open");
      opener.setAttribute("aria-expanded", "true");
    });
    drawer.addEventListener("close", function () {
      document.body.classList.remove("drawer-open");
      opener.setAttribute("aria-expanded", "false");
      opener.focus();
    });
    drawer.querySelector("[data-menu-close]").addEventListener("click", function () { drawer.close(); });
    drawer.addEventListener("click", function (e) {
      if (e.target === drawer) drawer.close();
      if (e.target.closest("a")) drawer.close();
    });
    if (location.hash === "#menu") opener.click();
  }

  initWiki();

  function initWiki() {
    var article = document.querySelector("[data-wiki-article]");
    var toggleBox = document.querySelector("[data-wiki-toggle]");
    if (toggleBox && window.matchMedia("(max-width: 48rem)").matches && !document.querySelector(".wiki-home")) {
      toggleBox.removeAttribute("open");
    }

    var tocNav = document.querySelector("[data-wiki-toc]");
    if (tocNav && article) {
      var heads = article.querySelectorAll("h2[id]");
      if (!heads.length) tocNav.closest(".wiki-toc").hidden = true;
      heads.forEach(function (h) {
        var a = document.createElement("a");
        a.href = "#" + h.id;
        a.textContent = h.textContent;
        tocNav.appendChild(a);
      });
      if ("IntersectionObserver" in window && heads.length) {
        var links = tocNav.querySelectorAll("a");
        var io = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            if (!en.isIntersecting) return;
            links.forEach(function (l) { l.classList.toggle("active", l.getAttribute("href") === "#" + en.target.id); });
          });
        }, { rootMargin: "0px 0px -70% 0px" });
        heads.forEach(function (h) { io.observe(h); });
      }
    }

    var input = document.querySelector("[data-wiki-search]");
    if (!input) return;
    var index = null;
    var links = document.querySelectorAll("[data-wiki-link]");
    var groups = document.querySelectorAll("[data-wiki-group]");
    var empty = document.querySelector("[data-wiki-empty]");

    function load() {
      if (index) return;
      index = {};
      fetch("search.json").then(function (r) { return r.json(); }).then(function (d) { index = d; filter(); }).catch(function () {});
    }

    function filter() {
      var words = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
      var any = false;
      links.forEach(function (l) {
        var hay = (index && index[l.dataset.slug]) || l.textContent.toLowerCase();
        var ok = words.every(function (w) { return hay.indexOf(w) !== -1; });
        l.hidden = !ok;
        if (ok) any = true;
      });
      groups.forEach(function (g) { g.hidden = !g.querySelector("[data-wiki-link]:not([hidden])"); });
      empty.hidden = any;
    }

    input.addEventListener("focus", load);
    input.addEventListener("input", filter);
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        var first = document.querySelector("[data-wiki-link]:not([hidden])");
        if (first) location.href = first.href;
      }
      if (e.key === "Escape") { input.value = ""; filter(); input.blur(); }
    });
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (toggleBox) toggleBox.setAttribute("open", "");
        input.focus();
      }
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
      packets: [{ pre: "мне на сервер", host: "203.0.113.7", post: "", addrOnly: true }],
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
