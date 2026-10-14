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
    var tag = event.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || event.altKey || event.ctrlKey || event.metaKey) {
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
    systemQuery.addEventListener("change", syncSwitch);
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

  function showFallback(box) {
    box.querySelector(".mermaid").hidden = true;
    box.querySelector(".diagram-fallback").hidden = false;
  }

  function drawDiagram(box, theme) {
    var pre = box.querySelector(".mermaid");
    if (pre.definition === undefined) {
      pre.definition = pre.textContent;
    }
    drawCount += 1;
    var id = "diagram-" + drawCount;
    window.mermaid
      .render(id, pre.definition)
      .then(function (result) {
        pre.innerHTML = result.svg;
      })
      .catch(function () {
        var leftover = document.getElementById("d" + id);
        if (leftover) {
          leftover.remove();
        }
        showFallback(box);
      });
  }

  /* Mermaid draws off screen, so diagrams on hidden slides and in print are drawn too. */
  function drawDiagrams() {
    var boxes = document.querySelectorAll(".diagram");
    if (!boxes.length) {
      return;
    }
    var theme = isDark() ? "dark" : "default";
    Array.prototype.forEach.call(boxes, function (box) {
      if (!window.mermaid) {
        showFallback(box);
        return;
      }
      try {
        window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: theme });
        drawDiagram(box, theme);
      } catch (e) {
        showFallback(box);
      }
    });
  }

  if (document.readyState === "complete") {
    drawDiagrams();
  } else {
    window.addEventListener("load", drawDiagrams);
  }
  showFromHash();
})();
