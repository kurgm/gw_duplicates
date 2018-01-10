document.addEventListener("DOMContentLoaded", function () {
  String.prototype.toCodePoints = function () {
    var i = 0,
      len = this.length,
      points = [];
    while (i < len) {
      var x = this.charCodeAt(i++);
      if (0xD800 <= x && x < 0xDC00) {
        var y = this.charCodeAt(i++);
        points.push(0x10000 + ((x & 0x3FF) << 10) | (y & 0x3FF));
      } else {
        points.push(x);
      }
    }
    return points;
  };
  String.fromCodePoint = function () {
    var i = 0,
      len = arguments.length,
      points = [];
    while (i < len) {
      var x = arguments[i++];
      if (x < 0x10000) {
        points.push(x);
      } else {
        x -= 0x10000;
        points.push(0xD800 | (x >> 10));
        points.push(0xDC00 | (x & 0x3FF));
      }
    }
    return String.fromCharCode.apply(String, points);
  };
  function glyphImage(name) {
    var a = document.createElement("a");
    var img = document.createElement("img");
    a.href = "https://glyphwiki.org/wiki/" + name;
    img.src = "https://glyphwiki.org/glyph/" + name + ".50px.png";
    img.alt = name;
    img.width = img.height = "50";
    a.appendChild(img);
    a.appendChild(document.createTextNode(name));
    return a;
  }
  var c_l = document.getElementsByClassName("collapsible-link");
  var c = function () {
    if (!this.dataset) { return; }
    var o = document.getElementById(this.dataset.colobj);
    var txt = o.classList.toggle("collapsed") ? "[表示]" : "[隠す]";
    while (this.firstChild) { this.removeChild(this.firstChild); }
    this.appendChild(document.createTextNode(txt));
  };
  for (var i = 0, l = c_l.length; i < l; i++) {
    c_l[i].addEventListener("click", c, false);
    if (c_l[i].dataset) {
      var o = document.getElementById(c_l[i].dataset.colobj);
      o.classList.add("collapsed");
    }
  }
  var xhr = new XMLHttpRequest();
  xhr.open("GET", "duplicates.json", true);
  xhr.responseType = "json";
  xhr.onload = function () {
    var json = xhr.response;
    // var list = json.buhin;
    var list = json.buhin.concat(json.kaku);
    for (var i = 0, l = list.length; i < l; i++) {
      list[i][4] = i;
    }
    var currentPage = 1, items_per_page = 100;
    var maxPage, searched_list;
    var search_text = "";
    function searchResult() {
      if (search_text === "") {
        searched_list = list;
      } else {
        if (search_text.match(/^[^\x00-\xFF]+$/)) {
          var cps = search_text.toCodePoints();
          for (var i = 0, l = cps.length; i < l; i++) {
            var hex = cps[i].toString(16);
            if (hex.length < 4) { hex = ("000" + hex).slice(-4); }
            cps[i] = "u" + hex;
          }
          search_text = "(^|-)" + cps.join("-") + "($|-)";
        }
        try {
          var re = new RegExp(search_text);
        } catch (e) {
          alert("正規表現にエラーがあります。\n\n" + e.message);
          return;
        }
        searched_list = [];
        for (var i = 0, l = list.length; i < l; i++) {
          var item = list[i];
          if (item[0].match(re) || item[1].match(re) || item[2] && item[2].match(re) || item[3] && item[3].match(re)) {
            searched_list.push(item);
          }
        }
      }
      maxPage = Math.ceil(searched_list.length / items_per_page);
    }
    searchResult();
    function showPage() {
      var df = document.createDocumentFragment();
      var i = (currentPage - 1) * items_per_page, m = Math.min(searched_list.length, currentPage * items_per_page);
      df.appendChild(document.createElement("div")).appendChild(document.createTextNode(
        "dump: " + new Date(json.timestamp * 1000).toLocaleString() + "; " +
        (m === 0
          ? "No items found"
          : ((i + 1) + "-" + m + " of " + searched_list.length + " item" + (searched_list.length === 1 ? "" : "s") + " shown below")
        )
      ));
      for (; i < m; i++) {
        var item = searched_list[i];
        var d = document.createElement("div");
        df.appendChild(d);
        var d2 = d.appendChild(document.createElement("div"));
        d2.appendChild(document.createTextNode(item[4] + 1 + ". "));
        d2.appendChild(glyphImage(item[0]));
        d2.appendChild(document.createTextNode((item[2] ? "(" + String.fromCodePoint(parseInt(item[2].slice(1), 16)) + ")" : "") + " vs. "));
        d2.appendChild(glyphImage(item[1]));
        d2.appendChild(document.createTextNode(item[3] ? "(" + String.fromCodePoint(parseInt(item[3].slice(1), 16)) + ")" : ""));
        var cd = d.appendChild(document.createElement("div"));
        cd.className = "control";
        var a;
        a = cd.appendChild(document.createElement("a"));
        a.href = "https://glyphwiki.org/wiki/" + item[1] + "?action=preview&related=" + (item[3] || "u3013") + "&textbox=%5B%5B" + item[0] + "%5D%5D&summary=" + item[0];
        a.target = "_new";
        a.appendChild(document.createTextNode("後者をエイリアスに"));
        cd.appendChild(document.createTextNode("／"));

        a = cd.appendChild(document.createElement("a"));
        a.href = "https://glyphwiki.org/wiki/" + item[0] + "?action=preview&related=" + (item[2] || "u3013") + "&textbox=%5B%5B" + item[1] + "%5D%5D&summary=" + item[1];
        a.target = "_new";
        a.appendChild(document.createTextNode("前者をエイリアスに"));
        cd.appendChild(document.createTextNode("／"));

        a = cd.appendChild(document.createElement("a"));
        a.href = "https://glyphwiki.org/wiki/" + item[0] + "?action=preview&textbox=0%3A0%3A0%3A0&summary=" + item[1];
        a.target = "_new";
        a.appendChild(document.createTextNode("前者を白紙化"));
        cd.appendChild(document.createTextNode("／"));

        a = cd.appendChild(document.createElement("a"));
        a.href = "https://glyphwiki.org/wiki/" + item[1] + "?action=preview&textbox=0%3A0%3A0%3A0&summary=" + item[0];
        a.target = "_new";
        a.appendChild(document.createTextNode("後者を白紙化"));
      }
      var res = document.getElementById("result");
      while (res.firstChild) { res.removeChild(res.firstChild); }
      res.appendChild(df);
      var prev_disabled = currentPage <= 1,
        next_disabled = currentPage >= maxPage;
      document.getElementById("page_first").disabled = prev_disabled;
      document.getElementById("page_prev").disabled = prev_disabled;
      document.getElementById("page_next").disabled = next_disabled;
      document.getElementById("page_last").disabled = next_disabled;
      var pageno = document.getElementById("page_no");
      while (pageno.firstChild) { pageno.removeChild(pageno.firstChild); }
      pageno.appendChild(document.createTextNode(currentPage + "/" + maxPage));
    }
    document.getElementById("page_first").addEventListener("click", function () {
      currentPage = 1;
      showPage();
    });
    document.getElementById("page_prev").addEventListener("click", function () {
      currentPage--;
      showPage();
    });
    document.getElementById("page_next").addEventListener("click", function () {
      currentPage++;
      showPage();
    });
    document.getElementById("page_last").addEventListener("click", function () {
      currentPage = maxPage;
      showPage();
    });
    document.getElementById("search_form").addEventListener("submit", function (evt) {
      search_text = document.getElementById("search_field").value;
      searchResult();
      currentPage = 1;
      showPage();
      evt.preventDefault();
    });
    document.getElementById("loading_msg").style.display = "none";
    showPage();
  };
  xhr.send(null);
}, false);
