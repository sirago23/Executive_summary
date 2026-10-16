(function () {
  var root = document.documentElement;
  root.className += " js";

  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var count = document.getElementById("count");
  var toc = document.querySelector(".toc");
  var current = 0;

  function read(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function write(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      /* storage can be blocked; the deck still works without it */
    }
  }

  function show(index) {
    if (!slides.length) {
      return;
    }
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach(function (slide, i) {
      slide.classList.toggle("active", i === current);
    });
    count.textContent = "Slide " + (current + 1) + " of " + slides.length;
    document.getElementById("prev").disabled = current === 0;
    document.getElementById("next").disabled = current === slides.length - 1;
    window.scrollTo(0, 0);
  }

  function showFromHash() {
    var id = window.location.hash.replace("#", "");
    for (var i = 0; i < slides.length; i++) {
      if (slides[i].id === id) {
        show(i);
        return;
      }
    }
    show(0);
  }

  document.getElementById("prev").addEventListener("click", function () {
    show(current - 1);
  });
  document.getElementById("next").addEventListener("click", function () {
    show(current + 1);
  });

  toc.addEventListener("click", function (event) {
    if (event.target.tagName === "A") {
      toc.removeAttribute("open");
    }
  });

  window.addEventListener("hashchange", showFromHash);

  document.addEventListener("keydown", function (event) {
    var target = event.target;
    var isTyping =
      target.tagName === "TEXTAREA" ||
      target.isContentEditable ||
      (target.tagName === "INPUT" && target.type !== "checkbox");
    if (isTyping || event.altKey || event.ctrlKey || event.metaKey) {
      return;
    }
    if (event.key === "ArrowRight" || event.key === "PageDown") {
      show(current + 1);
    } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
      show(current - 1);
    } else if (event.key === "Home") {
      show(0);
    } else if (event.key === "End") {
      show(slides.length - 1);
    }
  });

  var themeKey = "exec-summary:theme";
  var savedTheme = read(themeKey);
  if (savedTheme === "light" || savedTheme === "dark") {
    root.setAttribute("data-theme", savedTheme);
  }
  var themeSwitch = document.getElementById("theme");
  var systemQuery = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function isDark() {
    var explicit = root.getAttribute("data-theme");
    return explicit ? explicit === "dark" : !!(systemQuery && systemQuery.matches);
  }

  function syncSwitch() {
    themeSwitch.setAttribute("aria-checked", isDark() ? "true" : "false");
  }

  themeSwitch.addEventListener("click", function () {
    var next = isDark() ? "light" : "dark";
    root.setAttribute("data-theme", next);
    write(themeKey, next);
    syncSwitch();
    drawDiagrams();
  });
  if (systemQuery && systemQuery.addEventListener) {
    systemQuery.addEventListener("change", function () {
      syncSwitch();
      drawDiagrams();
    });
  }
  syncSwitch();

  var boxes = document.querySelectorAll("input[data-key]");
  Array.prototype.forEach.call(boxes, function (box) {
    box.checked = read(box.getAttribute("data-key")) === "1";
    box.addEventListener("change", function () {
      write(box.getAttribute("data-key"), box.checked ? "1" : "0");
    });
  });

  var drawCount = 0;
  var DRAW_TIMEOUT = 8000;

  /* A diagram box is "drawn" (picture shown) or "failed" (table of nodes and edges shown). With
     no state yet, a short "Drawing" text shows instead of the raw definition. */
  function setState(box, state) {
    box.setAttribute("data-state", state);
    box.querySelector(".diagram-fallback").hidden = state !== "failed";
  }

  /* Mermaid's "base" theme takes its colours from the same CSS tokens the deck uses, so diagrams
     match light and dark. To read the tokens of the other mode, data-theme is switched for an
     instant and put back before anything is painted. */
  function diagramTheme(mode) {
    var saved = root.getAttribute("data-theme");
    root.setAttribute("data-theme", mode);
    var style = window.getComputedStyle(root);
    function token(name) {
      return style.getPropertyValue(name).trim();
    }
    var theme = {
      theme: "base",
      themeVariables: {
        background: token("--surface"),
        primaryColor: token("--card"),
        primaryTextColor: token("--text"),
        primaryBorderColor: token("--accent"),
        secondaryColor: token("--accent-soft"),
        tertiaryColor: token("--surface"),
        textColor: token("--text"),
        lineColor: token("--muted"),
        mainBkg: token("--card"),
        nodeBorder: token("--accent"),
        clusterBkg: token("--accent-soft"),
        clusterBorder: token("--line"),
        edgeLabelBackground: token("--surface"),
        titleColor: token("--text"),
      },
    };
    if (saved === null) {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", saved);
    }
    return theme;
  }

  function renderSvg(definition, theme) {
    drawCount += 1;
    var id = "diagram-" + drawCount;
    /* The theme travels with each definition, so overlapping draws cannot mix themes up. */
    var config = theme;
    if (/^\s*flowchart LR/.test(definition)) {
      /* A flow drawn left to right gets narrow boxes, so a long one fits the slide at a readable size. */
      config = Object.assign({}, theme, { flowchart: { wrappingWidth: 130 } });
    }
    var text = "%%{init: " + JSON.stringify(config) + "}%%\n" + definition;
    return window.mermaid.render(id, text).then(
      function (result) {
        return result.svg;
      },
      function (error) {
        var leftover = document.getElementById("d" + id);
        if (leftover) {
          leftover.remove();
        }
        throw error;
      }
    );
  }

  /* Mermaid draws off screen, so diagrams on hidden slides are drawn too. Each diagram is drawn
     twice: once in the current theme for the screen, once light for printing. */
  function drawDiagram(box, theme) {
    var pre = box.querySelector(".mermaid");
    var printed = box.querySelector(".mermaid-print");
    if (pre.definition === undefined) {
      pre.definition = pre.textContent;
    }
    Promise.all([renderSvg(pre.definition, theme), renderSvg(pre.definition, diagramTheme("light"))])
      .then(function (svgs) {
        pre.innerHTML = svgs[0];
        printed.innerHTML = svgs[1];
        setState(box, "drawn");
      })
      .catch(function () {
        setState(box, "failed");
      });
  }

  function drawDiagrams() {
    var boxes = document.querySelectorAll(".diagram");
    if (!boxes.length) {
      return;
    }
    var theme = diagramTheme(isDark() ? "dark" : "light");
    Array.prototype.forEach.call(boxes, function (box) {
      if (!window.mermaid) {
        setState(box, "failed");
        return;
      }
      try {
        window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
        drawDiagram(box, theme);
      } catch (e) {
        setState(box, "failed");
      }
    });
  }

  /* If Mermaid is slow to load, show the table. A later successful draw replaces it. */
  window.setTimeout(function () {
    Array.prototype.forEach.call(document.querySelectorAll(".diagram:not([data-state])"), function (box) {
      setState(box, "failed");
    });
  }, DRAW_TIMEOUT);

  if (document.readyState === "complete") {
    drawDiagrams();
  } else {
    window.addEventListener("load", drawDiagrams);
  }
  showFromHash();
})();
