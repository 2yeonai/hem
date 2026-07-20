// RTS 복습·실기 연습 앱 — 단일 파일 SPA (해시 라우팅), 데이터는 data.json에서 로드
(function () {
  "use strict";

  var DATA = null;
  var VIZ = null;          // viz_data.json cards (파생: 자세/화살표/체인)
  var MMAP = null;         // muscle_map.json cards (부위/메시 매핑)
  var ASSESS_INDEX = [];   // {norm, id}
  var TECH_INDEX = [];     // {norm, id}
  var QUIZ_POOL = [];
  var LS_KEY = "rts_weakness_v1";

  // ---------- 유틸 ----------
  function normalize(s) {
    return String(s || "").replace(/\s+/g, "").toLowerCase();
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function nl2br(s) {
    return esc(s).replace(/\n/g, "<br>");
  }
  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function sample(arr, n) {
    return shuffle(arr).slice(0, n);
  }
  function splitRespectingParens(s) {
    var out = [], depth = 0, cur = "";
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (c === "(") depth++;
      if (c === ")") depth = Math.max(0, depth - 1);
      if (c === "," && depth === 0) { out.push(cur); cur = ""; }
      else cur += c;
    }
    if (cur.trim()) out.push(cur);
    return out;
  }
  function parseArrowField(raw) {
    if (!raw) return [];
    if (Array.isArray(raw)) {
      return raw.map(function (s) { return String(s).replace(/\(.*?\)/g, "").trim(); }).filter(Boolean);
    }
    var s = String(raw);
    var m = s.match(/\[([\s\S]*)\]/);
    var inner = m ? m[1] : s;
    if (/^미기재/.test(inner.trim())) return [];
    return splitRespectingParens(inner).map(function (x) {
      return x.replace(/\(.*?\)/g, "").replace(/^["']|["']$/g, "").trim();
    }).filter(function (x) { return x && x !== "미기재"; });
  }
  function firstLine(text) {
    if (!text) return "";
    var lines = text.split("\n").map(function (l) { return l.replace(/^[-*①②③④⑤⑥⑦⑧⑨\s]+/, "").trim(); }).filter(Boolean);
    return lines[0] || "";
  }
  function truncate(s, n) {
    s = s || "";
    return s.length > n ? s.slice(0, n) + "…" : s;
  }
  // data.json의 F3_이미지 경로(../app/images/xxx.jpg, 카드 md 기준)를
  // app/index.html이 app/ 안에서 서빙되는 실제 환경(images/xxx.jpg)에 맞게 변환
  function f3ImagePath(p) {
    return String(p || "").replace("../app/images/", "images/");
  }
  function renderF3Images(images) {
    if (!images || !images.length) return "";
    var html = '<div class="card"><div class="chainlabel">📷 F3 참고 이미지 (소책자 손 위치·압력 방향)</div><div class="f3-images">';
    images.forEach(function (p) {
      var src = f3ImagePath(p);
      html += '<img class="f3-img" src="' + esc(src) + '" alt="F3 참고 이미지(손 위치·압력 방향)">';
    });
    html += '</div></div>';
    return html;
  }

  // ---------- 약점(오답) 저장소 ----------
  function loadWeakness() {
    try { return JSON.parse(localStorage.getItem(LS_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function saveWeakness(w) {
    localStorage.setItem(LS_KEY, JSON.stringify(w));
  }
  function recordAttempt(cardId, cardTitle, cardKind, correct) {
    var w = loadWeakness();
    if (!w[cardId]) w[cardId] = { title: cardTitle, kind: cardKind, seen: 0, correct: 0, wrong: 0, lastSeen: 0 };
    w[cardId].seen++;
    if (correct) w[cardId].correct++; else w[cardId].wrong++;
    w[cardId].lastSeen = Date.now();
    w[cardId].title = cardTitle;
    w[cardId].kind = cardKind;
    saveWeakness(w);
  }
  function weaknessList() {
    var w = loadWeakness();
    return Object.keys(w).map(function (id) {
      var e = w[id];
      var acc = e.seen ? e.correct / e.seen : 0;
      return { id: id, title: e.title, kind: e.kind, seen: e.seen, correct: e.correct, wrong: e.wrong, acc: acc, lastSeen: e.lastSeen };
    });
  }

  // ---------- 데이터 로딩 & 인덱스 ----------
  function buildIndices() {
    DATA.assessments.forEach(function (a) {
      var raw = a.frontmatter["검사명"] || a.title;
      String(raw).split("/").forEach(function (n) {
        n = n.trim(); if (n) ASSESS_INDEX.push({ norm: normalize(n), id: a.id });
      });
    });
    DATA.techniques.forEach(function (t) {
      var raw = t.frontmatter["근육명"] || t.title;
      String(raw).split("/").forEach(function (n) {
        n = n.trim(); if (n) TECH_INDEX.push({ norm: normalize(n), id: t.id });
      });
      if (t.frontmatter["근육명_영문"]) {
        TECH_INDEX.push({ norm: normalize(t.frontmatter["근육명_영문"]), id: t.id });
      }
    });
  }
  function findAssessmentByName(name) {
    var n = normalize(name);
    if (!n) return null;
    var hit = ASSESS_INDEX.find(function (x) { return x.norm === n; });
    if (!hit) hit = ASSESS_INDEX.find(function (x) { return x.norm.length > 1 && (x.norm.indexOf(n) >= 0 || n.indexOf(x.norm) >= 0); });
    return hit ? getAssessment(hit.id) : null;
  }
  function findTechniqueByMuscle(name) {
    var n = normalize(name);
    if (!n) return null;
    var hit = TECH_INDEX.find(function (x) { return x.norm === n; });
    if (!hit) hit = TECH_INDEX.find(function (x) { return x.norm.length > 1 && (x.norm.indexOf(n) >= 0 || n.indexOf(x.norm) >= 0); });
    return hit ? getTechnique(hit.id) : null;
  }
  function getAssessment(id) { return DATA.assessments.find(function (a) { return a.id === id; }); }
  function getTechnique(id) { return DATA.techniques.find(function (t) { return t.id === id; }); }

  // ---------- 퀴즈 풀 생성 ----------
  function buildQuizPool() {
    var pool = [];

    // A. 검사 -> 양성 판단
    DATA.assessments.forEach(function (a) {
      var correctText = firstLine(a.sections["양성 판단"]);
      if (!correctText) return;
      var others = DATA.assessments.filter(function (x) { return x.id !== a.id; });
      var distractors = sample(others, 3).map(function (x) { return firstLine(x.sections["양성 판단"]) || "(자료 없음)"; });
      var choices = shuffle([correctText].concat(distractors));
      pool.push({
        kind: "assessment", cardId: a.id, cardTitle: a.frontmatter["검사명"] || a.title,
        prompt: "「" + (a.frontmatter["검사명"] || a.title).split("/")[0].trim() + "」의 양성 판단 기준으로 옳은 것은?",
        choices: choices, answer: correctText
      });
    });

    // B. 검사 -> 의심 근육
    DATA.assessments.forEach(function (a) {
      var suspects = parseArrowField(a.frontmatter["의심근육→"]);
      if (!suspects.length) return;
      var correct = suspects[Math.floor(Math.random() * suspects.length)];
      var pool2 = [];
      DATA.assessments.forEach(function (x) {
        if (x.id === a.id) return;
        parseArrowField(x.frontmatter["의심근육→"]).forEach(function (m) { if (suspects.indexOf(m) < 0) pool2.push(m); });
      });
      pool2 = Array.from(new Set(pool2));
      if (pool2.length < 3) return;
      var distractors = sample(pool2, 3);
      var choices = shuffle([correct].concat(distractors));
      pool.push({
        kind: "assessment", cardId: a.id, cardTitle: a.frontmatter["검사명"] || a.title,
        prompt: "「" + (a.frontmatter["검사명"] || a.title).split("/")[0].trim() + "」 양성일 때 확인할 의심 근육으로 알맞은 것은?",
        choices: choices, answer: correct
      });
    });

    // C. 테크닉 -> "이 사람에게 해!" 문구로 근육 맞히기
    DATA.techniques.forEach(function (t) {
      var line = firstLine(t.sections["이 사람에게 해!"]);
      if (!line) return;
      var correct = (t.frontmatter["근육명"] || t.title).split("/")[0].trim();
      var others = DATA.techniques.filter(function (x) { return x.id !== t.id; });
      var distractors = sample(others, 3).map(function (x) { return (x.frontmatter["근육명"] || x.title).split("/")[0].trim(); });
      var choices = shuffle([correct].concat(distractors));
      pool.push({
        kind: "technique", cardId: t.id, cardTitle: t.frontmatter["근육명"] || t.title,
        prompt: '다음 특징에 해당하는 근육은?\n"' + line + '"',
        choices: choices, answer: correct
      });
    });

    // D. 테크닉 -> 핵심 한 줄로 근육 맞히기
    DATA.techniques.forEach(function (t) {
      var line = firstLine(t.sections["핵심 한 줄"]);
      if (!line) return;
      var correct = (t.frontmatter["근육명"] || t.title).split("/")[0].trim();
      var others = DATA.techniques.filter(function (x) { return x.id !== t.id; });
      var distractors = sample(others, 3).map(function (x) { return (x.frontmatter["근육명"] || x.title).split("/")[0].trim(); });
      var choices = shuffle([correct].concat(distractors));
      pool.push({
        kind: "technique", cardId: t.id, cardTitle: t.frontmatter["근육명"] || t.title,
        prompt: '다음 핵심 한 줄 설명에 해당하는 근육은?\n"' + line + '"',
        choices: choices, answer: correct
      });
    });

    QUIZ_POOL = pool;
  }

  // ---------- 라우터 ----------
  function route() {
    var hash = location.hash.replace(/^#/, "") || "/home";
    var parts = hash.split("/").filter(Boolean);
    var app = document.getElementById("app");
    var crumb = document.getElementById("crumb");
    document.querySelectorAll(".navbar a").forEach(function (a) {
      a.classList.toggle("active", a.dataset.route === parts[0]);
    });
    crumb.innerHTML = "";
    // 3D 뷰어는 model 상세에서만 살아있게: 다른 라우트로 가면 정리(모델 상세는 곧바로 재마운트)
    if (window.RTSViz && !(parts[0] === "model" && parts[1])) RTSViz.unmount();

    if (parts[0] === "home" || parts.length === 0) return renderHome(app);
    if (parts[0] === "assessments") return renderAssessmentList(app, crumb);
    if (parts[0] === "assessment" && parts[1]) return renderAssessmentDetail(app, crumb, parts[1]);
    if (parts[0] === "techniques") return renderTechniqueList(app, crumb);
    if (parts[0] === "technique" && parts[1]) return renderTechniqueDetail(app, crumb, parts[1]);
    if (parts[0] === "quiz") return renderQuizStart(app, crumb);
    if (parts[0] === "quizrun") return renderQuizRun(app, crumb, parts[1]);
    if (parts[0] === "review") return renderReview(app, crumb);
    if (parts[0] === "search") return renderSearch(app, crumb, decodeURIComponent(parts[1] || ""));
    if (parts[0] === "model" && parts[1]) return renderModelDetail(app, crumb, parts[1]);
    if (parts[0] === "model") return renderModelHome(app, crumb);
    app.innerHTML = '<div class="empty">페이지를 찾을 수 없습니다.</div>';
  }

  // ---------- 3D 모델 뷰어 ----------
  function vizCard(id) { return VIZ && VIZ.cards ? VIZ.cards[id] : null; }
  function mapCard(id) { return MMAP && MMAP.cards ? MMAP.cards[id] : null; }

  function muscleLabel(id) {
    var v = vizCard(id);
    if (v && v.muscle) {
      var old = v.muscle.old || v.muscle.new || "";
      var sci = v.muscle.sci || v.muscle.en || "";
      return old + (sci ? " / " + sci : "");
    }
    var t = getTechnique(id);
    return t ? (t.frontmatter["근육명"] || t.title) : id;
  }

  function renderModelHome(app, crumb) {
    crumb.innerHTML = "<b>3D 자세·근육 모델</b>";
    var html = "";
    html += '<div class="card"><h2>🧍 3D 자세·근육 모델</h2>';
    html += '<p class="muted">근육을 고르면 그 테크닉을 할 때의 <b>대상자 자세</b>를 마네킹이 재현하고, <b>타깃 부위</b>를 빨갛게 강조합니다. 화면을 드래그하면 돌려볼 수 있어요.</p>';
    html += '<p class="muted" style="font-size:12px">※ 부위 단위 강조 + 일부 근육은 실제 형상(Z-Anatomy 메시, CC BY-SA)도 함께 표시됩니다. 관절별 자세 연동은 아직 없어 실제 근육 모양은 전신 방향만 대략 따라갑니다.</p></div>';

    // 부위(mesh 상위)별 그룹핑
    var groups = { "목": [], "어깨·등": [], "가슴·코어": [], "엉덩이·골반": [], "허벅지": [], "종아리·발": [] };
    function bucket(region) {
      var r = (region || "").toLowerCase();
      if (/neck|head/.test(r)) return "목";
      if (/torsoupper/.test(r)) return "어깨·등";
      if (/torsolower/.test(r)) return "가슴·코어";
      if (/pelvis/.test(r)) return "엉덩이·골반";
      if (/thigh/.test(r)) return "허벅지";
      if (/shin|foot/.test(r)) return "종아리·발";
      return "가슴·코어";
    }
    DATA.techniques.forEach(function (t) {
      var mc = mapCard(t.id);
      if (!mc) return;
      var g = bucket((mc.mesh || [])[0]);
      // 가슴/코어 세분: 가슴은 torsoUpper front지만 어깨·등과 겹침 → region_ko로 보정
      if (/가슴|배|허리|호흡|골반 바닥/.test(mc.region_ko) && g === "어깨·등") g = "가슴·코어";
      groups[g].push({ t: t, mc: mc });
    });
    Object.keys(groups).forEach(function (gname) {
      if (!groups[gname].length) return;
      html += '<div class="section-title">' + esc(gname) + '</div><div class="grid">';
      groups[gname].forEach(function (o) {
        var name = (o.t.frontmatter["근육명"] || o.t.title).split("/")[0].trim();
        html += '<a href="#/model/' + encodeURIComponent(o.t.id) + '"><div class="tile"><b>' + esc(name) + '</b>' +
          '<small>' + esc(o.mc.region_ko || "") + '</small></div></a>';
      });
      html += "</div>";
    });
    app.innerHTML = html;
  }

  function renderModelDetail(app, crumb, rawId) {
    var id = decodeURIComponent(rawId);
    var isTech = id.indexOf("technique") === 0;
    var card = isTech ? getTechnique(id) : getAssessment(id);
    if (!card) { app.innerHTML = '<div class="empty">카드를 찾을 수 없습니다.</div>'; return; }
    var v = vizCard(id);
    var mc = mapCard(id);

    // 검사카드면: 자세는 검사 자세, 강조는 첫 의심근육의 부위
    var poseTag = (v && v.primary_pose_tag) || "서기";
    var meshKeys = [], face = "front", label = "", regionKo = "", zAnatomy = "";
    var focusMuscleId = id;
    if (isTech && mc) {
      meshKeys = mc.mesh; face = mc.face; regionKo = mc.region_ko;
      label = muscleLabel(id); zAnatomy = mc.z_anatomy || "";
    } else if (!isTech && v) {
      var suspects = (v.chain && v.chain.suspect_muscles) || [];
      var mt = null;
      for (var i = 0; i < suspects.length; i++) { mt = findTechniqueByMuscle(suspects[i]); if (mt) break; }
      if (mt) {
        var mmc = mapCard(mt.id);
        if (mmc) { meshKeys = mmc.mesh; face = mmc.face; regionKo = mmc.region_ko; label = muscleLabel(mt.id); focusMuscleId = mt.id; zAnatomy = mmc.z_anatomy || ""; }
      }
    }

    var name = isTech ? (card.frontmatter["근육명"] || card.title).split("/")[0].trim()
                      : (card.frontmatter["검사명"] || card.title).split("/")[0].trim();
    crumb.innerHTML = '<a href="#/model">3D 모델</a> › <b>' + esc(name) + '</b>';

    var html = "";
    html += '<div class="viz-wrap">';
    html += '<div class="viz-canvas-box"><canvas id="vizCanvas"></canvas>';
    html += '<div class="viz-poselabel" id="vizPoseLabel"></div></div>';
    html += '<div class="viz-panel" id="vizPanel"></div>';
    html += '</div>';
    app.innerHTML = html;

    // 패널 내용
    var panel = document.getElementById("vizPanel");
    var ph = "";
    ph += '<div class="card">';
    ph += '<h2 style="margin:0 0 4px">' + esc(name) + '</h2>';
    if (label) ph += '<div class="viz-label">🏷 ' + esc(label) + '</div>';
    if (regionKo) ph += '<div class="muted" style="font-size:13px">부위: ' + esc(regionKo) + '</div>';
    ph += '</div>';

    // 자세 프리셋 버튼
    ph += '<div class="card"><div class="chainlabel">🧍 대상자 자세 프리셋</div><div class="viz-poses">';
    (window.RTSViz ? RTSViz.poses : ["서기"]).forEach(function (p) {
      ph += '<button class="pose-btn' + (p === poseTag ? " active" : "") + '" data-pose="' + esc(p) + '">' + esc(p) + '</button>';
    });
    ph += '</div>';
    if (v && v.poses && v.poses.length) {
      ph += '<div class="muted" style="font-size:12px;margin-top:6px">원문 자세: ';
      ph += v.poses.map(function (p) { return esc(p.section) + "→" + esc(p.pose_tag || "미분류"); }).join(" · ");
      ph += '</div>';
    }
    ph += '</div>';

    // 카드 핵심 내용
    var sec = card.sections || {};
    function block(title, key) {
      if (!sec[key]) return "";
      return '<div class="viz-sec"><div class="viz-sec-t">' + esc(title) + '</div>' + nl2br(truncate(sec[key], 420)) + '</div>';
    }
    ph += '<div class="card">';
    if (isTech) {
      ph += block("촉진", "촉진 (Palpation)") + block("ART", "ART 1") + block("MET", "MET 1") + block("MET", "MET");
      Object.keys(sec).forEach(function (k) { if (/^운동/.test(k)) ph += block(k, k); });
    } else {
      ph += block("자세", "자세") + block("방법", "방법") + block("양성 판단", "양성 판단");
    }
    ph += '</div>';

    // 화살표 힌트
    if (v && v.arrow_hints && v.arrow_hints.length) {
      ph += '<div class="card"><div class="chainlabel">➡️ 손 방향·스트로크 힌트</div>';
      v.arrow_hints.slice(0, 4).forEach(function (h) {
        ph += '<div class="viz-arrow">↳ ' + esc(truncate(h.text, 90)) + '</div>';
      });
      ph += '</div>';
    }

    // 체인 버튼
    ph += '<div class="card chainbox">';
    var v2 = v || {};
    var suspects = (v2.chain && v2.chain.suspect_muscles) || [];
    var retests = (v2.chain && v2.chain.retests) || [];
    ph += '<div class="chainlabel">🧠 함께 볼 근육(3D)</div>';
    if (suspects.length) {
      ph += suspects.map(function (mname) {
        var mt = findTechniqueByMuscle(mname);
        if (mt) return '<a href="#/model/' + encodeURIComponent(mt.id) + '"><span class="chip type-muscle">🧍 ' + esc(mname) + '</span></a>';
        return '<span class="chip disabled">🧍 ' + esc(mname) + '</span>';
      }).join("");
    } else { ph += '<span class="muted">기재 없음</span>'; }
    ph += '<div class="chainlabel">🔁 재검사</div>';
    if (retests.length) {
      ph += retests.map(function (rn) {
        var ra = findAssessmentByName(rn);
        if (ra) return '<a href="#/assessment/' + encodeURIComponent(ra.id) + '"><span class="chip type-assess">🩺 ' + esc(rn) + '</span></a>';
        return '<span class="chip disabled">🩺 ' + esc(rn) + '</span>';
      }).join("");
    } else { ph += '<span class="muted">기재 없음</span>'; }
    ph += '</div>';

    ph += '<div class="btnrow">';
    var detailLink = isTech ? "#/technique/" + encodeURIComponent(id) : "#/assessment/" + encodeURIComponent(id);
    ph += '<a href="' + detailLink + '"><button class="secondary">카드 상세 보기</button></a></div>';
    panel.innerHTML = ph;

    // 3D 마운트
    if (!window.RTSViz || !window.THREE) {
      document.getElementById("vizPoseLabel").textContent = "3D 엔진 로드 실패";
      return;
    }
    var canvas = document.getElementById("vizCanvas");
    RTSViz.unmount();
    RTSViz.mount(canvas);
    var applied = RTSViz.setPose(poseTag);
    RTSViz.setHighlight(meshKeys, face, label, zAnatomy);
    var poseLabelEl = document.getElementById("vizPoseLabel");
    poseLabelEl.textContent = "자세: " + poseTag + (applied !== poseTag ? " (기본)" : "");

    panel.querySelectorAll(".pose-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        var pt = b.dataset.pose;
        panel.querySelectorAll(".pose-btn").forEach(function (x) { x.classList.toggle("active", x === b); });
        RTSViz.setPose(pt);
        RTSViz.setHighlight(meshKeys, face, label, zAnatomy);
        poseLabelEl.textContent = "자세: " + pt;
      });
    });
  }

  // ---------- 홈 ----------
  function renderHome(app) {
    var wl = weaknessList().filter(function (w) { return w.seen > 0; });
    wl.sort(function (a, b) { return a.acc - b.acc || b.wrong - a.wrong; });
    var top5 = wl.slice(0, 5);
    var avgAcc = wl.length ? Math.round(100 * wl.reduce(function (s, w) { return s + w.acc; }, 0) / wl.length) : 0;

    var html = "";
    html += '<div class="card">';
    html += '<div class="hp-row">';
    html += '<div class="stat"><b>' + DATA.assessments.length + '</b><small>검사 카드</small></div>';
    html += '<div class="stat"><b>' + DATA.techniques.length + '</b><small>테크닉 카드</small></div>';
    html += '<div class="stat"><b>' + avgAcc + '%</b><small>퀴즈 정답률</small></div>';
    html += '</div></div>';

    html += '<div class="section-title">오늘의 복습 큐 (약점 Top 5)</div>';
    if (!top5.length) {
      html += '<div class="empty">아직 퀴즈 기록이 없습니다. 퀴즈를 풀면 여기 약점이 표시돼요.<br><br><a href="#/quiz"><button>퀴즈 시작하기</button></a></div>';
    } else {
      top5.forEach(function (w) {
        var link = w.kind === "assessment" ? "#/assessment/" + w.id : "#/technique/" + w.id;
        html += '<a href="' + link + '"><div class="card"><b>' + esc((w.title + "").split("/")[0].trim()) + '</b>' +
          ' <span class="pill">' + w.correct + '/' + w.seen + ' 정답</span></div></a>';
      });
    }

    html += '<div class="section-title">빠른 이동</div>';
    html += '<div class="grid">';
    html += '<a href="#/assessments"><div class="tile">🩺<b>검사 라이브러리</b><small>' + DATA.assessments.length + '종</small></div></a>';
    html += '<a href="#/techniques"><div class="tile">✋<b>테크닉 라이브러리</b><small>' + DATA.techniques.length + '종</small></div></a>';
    html += '<a href="#/quiz"><div class="tile">📝<b>퀴즈</b><small>체인 복습</small></div></a>';
    html += '<a href="#/review"><div class="tile">📌<b>오답노트</b><small>' + wl.filter(function (w) { return w.wrong > 0; }).length + '건</small></div></a>';
    html += '</div>';

    app.innerHTML = html;
  }

  // ---------- 검사 라이브러리 ----------
  function renderAssessmentList(app, crumb) {
    crumb.innerHTML = "<b>검사 라이브러리</b>";
    var byPart = {};
    DATA.assessments.forEach(function (a) {
      var part = (a.frontmatter["파트"] || "기타").toString().replace(/^PART\s*\d+\s*[—-]\s*/, "");
      if (!byPart[part]) byPart[part] = [];
      byPart[part].push(a);
    });
    var html = "";
    Object.keys(byPart).forEach(function (part) {
      html += '<div class="section-title">' + esc(part) + '</div><div class="grid">';
      byPart[part].forEach(function (a) {
        var lvl = a.frontmatter["레벨"];
        var name = (a.frontmatter["검사명"] || a.title).split("/")[0].trim();
        html += '<a href="#/assessment/' + encodeURIComponent(a.id) + '"><div class="tile"><b>' + esc(name) + '</b>' +
          '<span class="pill lvl' + esc(lvl) + '">Lv.' + esc(lvl) + '</span></div></a>';
      });
      html += "</div>";
    });
    app.innerHTML = html;
  }

  function chainChip(name, kind) {
    if (kind === "assessment") {
      var a = findAssessmentByName(name);
      if (a) return '<a href="#/assessment/' + encodeURIComponent(a.id) + '"><span class="chip type-assess">🩺 ' + esc(name) + '</span></a>';
      return '<span class="chip disabled">🩺 ' + esc(name) + '</span>';
    } else {
      var t = findTechniqueByMuscle(name);
      if (t) return '<a href="#/technique/' + encodeURIComponent(t.id) + '"><span class="chip type-muscle">✋ ' + esc(name) + '</span></a>';
      return '<span class="chip disabled">✋ ' + esc(name) + '</span>';
    }
  }

  function renderAssessmentDetail(app, crumb, id) {
    var a = getAssessment(decodeURIComponent(id));
    if (!a) { app.innerHTML = '<div class="empty">카드를 찾을 수 없습니다.</div>'; return; }
    crumb.innerHTML = '<a href="#/assessments">검사</a> › <b>' + esc((a.frontmatter["검사명"] || a.title).split("/")[0].trim()) + '</b>';

    var order = ["대상", "자세", "방법", "보상 / 관찰 포인트", "정상 기준", "양성 판단", "의심 원인", "검사 시 주의", "비고 / 임상"];
    var tabsHtml = "", panelsHtml = "", first = true;
    order.forEach(function (key) {
      if (!a.sections[key]) return;
      tabsHtml += '<div class="tab' + (first ? " active" : "") + '" data-tab="' + esc(key) + '">' + esc(key) + '</div>';
      panelsHtml += '<div class="tabpanel" data-panel="' + esc(key) + '" style="' + (first ? "" : "display:none") + '">' + nl2br(a.sections[key]) + '</div>';
      first = false;
    });

    var suspects = parseArrowField(a.frontmatter["의심근육→"]);
    var relatedAssess = parseArrowField(a.frontmatter["연관검사→"]);
    var lvl = a.frontmatter["레벨"];

    var html = "";
    html += '<div class="card">';
    html += '<span class="pill lvl' + esc(lvl) + '">Lv.' + esc(lvl) + '</span> ';
    html += '<span class="pill">' + esc(a.frontmatter["관절"] || "") + '</span>';
    html += '<h2 style="margin-top:8px">' + esc((a.frontmatter["검사명"] || a.title).split("/")[0].trim()) + '</h2>';
    html += '<div class="muted" style="font-size:13px">' + esc(a.frontmatter["검사명"] || "") + '</div>';
    html += '</div>';

    html += '<div class="card"><div class="tabs">' + tabsHtml + '</div>' + panelsHtml + '</div>';

    html += '<div class="card chainbox">';
    html += '<div class="chainlabel">👉 이 검사가 양성이면 의심되는 근육</div>';
    html += suspects.length ? suspects.map(function (m) { return chainChip(m, "technique"); }).join("") : '<span class="muted">기재 없음</span>';
    html += '<div class="chainlabel">🔁 연관 검사</div>';
    html += relatedAssess.length ? relatedAssess.map(function (m) { return chainChip(m, "assessment"); }).join("") : '<span class="muted">기재 없음</span>';
    html += '</div>';

    html += '<div class="btnrow"><a href="#/model/' + encodeURIComponent(a.id) + '"><button>🧍 3D 자세·의심근육 보기</button></a>' +
      '<a href="#/quiz"><button class="secondary">이 카드로 퀴즈 풀기 준비</button></a></div>';

    app.innerHTML = html;
    bindTabs(app);
  }

  // ---------- 테크닉 라이브러리 ----------
  function renderTechniqueList(app, crumb) {
    crumb.innerHTML = "<b>테크닉 라이브러리</b>";
    var byPart = {};
    DATA.techniques.forEach(function (t) {
      var part = (t.frontmatter["파트"] || "기타").toString().replace(/^PART\s*\d+\s*[—-]\s*/, "");
      if (!byPart[part]) byPart[part] = [];
      byPart[part].push(t);
    });
    var html = "";
    Object.keys(byPart).forEach(function (part) {
      html += '<div class="section-title">' + esc(part) + '</div><div class="grid">';
      byPart[part].forEach(function (t) {
        var name = (t.frontmatter["근육명"] || t.title).split("/")[0].trim();
        html += '<a href="#/technique/' + encodeURIComponent(t.id) + '"><div class="tile"><b>' + esc(name) + '</b>' +
          '<small>' + esc(t.frontmatter["근육명_영문"] || "") + '</small></div></a>';
      });
      html += "</div>";
    });
    app.innerHTML = html;
  }

  function renderTechniqueDetail(app, crumb, id) {
    var t = getTechnique(decodeURIComponent(id));
    if (!t) { app.innerHTML = '<div class="empty">카드를 찾을 수 없습니다.</div>'; return; }
    crumb.innerHTML = '<a href="#/techniques">테크닉</a> › <b>' + esc((t.frontmatter["근육명"] || t.title).split("/")[0].trim()) + '</b>';

    var order = ["이 사람에게 해!", "핵심 한 줄", "짧아지는 자세 vs 늘어나는 자세", "촉진 (Palpation)",
      "ART 1", "ART 2", "MET", "MET 1", "임상 포인트", "금기 · 주의", "한 줄 정리"];
    var tabsHtml = "", panelsHtml = "", first = true;
    order.forEach(function (key) {
      if (!t.sections[key]) return;
      tabsHtml += '<div class="tab' + (first ? " active" : "") + '" data-tab="' + esc(key) + '">' + esc(key) + '</div>';
      panelsHtml += '<div class="tabpanel" data-panel="' + esc(key) + '" style="' + (first ? "" : "display:none") + '">' + nl2br(t.sections[key]) + '</div>';
      first = false;
    });
    Object.keys(t.sections).forEach(function (key) {
      // F3 참고 이미지 섹션은 원문이 마크다운 이미지 문법(![...](...))이라
      // 텍스트 탭으로 두면 그대로 이스케이프돼 깨져 보임 — 아래 renderF3Images()로 실제 <img> 렌더링하므로 중복 텍스트 탭에서는 제외
      if (order.indexOf(key) >= 0 || key === "체인 링크" || key === "F3 참고 이미지 (소책자)") return;
      tabsHtml += '<div class="tab" data-tab="' + esc(key) + '">' + esc(key) + '</div>';
      panelsHtml += '<div class="tabpanel" data-panel="' + esc(key) + '" style="display:none">' + nl2br(t.sections[key]) + '</div>';
    });

    var suspectMuscles = parseArrowField(t.frontmatter["의심근육→"]);
    var retest = parseArrowField(t.frontmatter["재검사→"]);

    var html = "";
    html += '<div class="card">';
    html += '<span class="pill">' + esc(t.frontmatter["테크닉_유형"] || "") + '</span>';
    html += '<h2 style="margin-top:8px" id="muscleName">' + esc((t.frontmatter["근육명"] || t.title).split("/")[0].trim()) + '</h2>';
    html += '<span class="hide-toggle" id="hideToggle">🙈 이름 가리고 암기 연습</span>';
    html += '<div class="muted" style="font-size:13px">' + esc(t.frontmatter["근육명"] || "") + " · " + esc(t.frontmatter["근육명_영문"] || "") + '</div>';
    html += '</div>';

    html += '<div class="card"><div class="tabs">' + tabsHtml + '</div>' + panelsHtml + '</div>';

    html += renderF3Images(t.frontmatter["F3_이미지"]);

    html += '<div class="card chainbox">';
    html += '<div class="chainlabel">🧠 이 근육이 뻣뻣하면 함께 볼 근육</div>';
    html += suspectMuscles.length ? suspectMuscles.map(function (m) { return chainChip(m, "technique"); }).join("") : '<span class="muted">기재 없음</span>';
    html += '<div class="chainlabel">🔁 테크닉 후 재검사</div>';
    html += retest.length ? retest.map(function (m) { return chainChip(m, "assessment"); }).join("") : '<span class="muted">기재 없음</span>';
    html += '</div>';

    html += '<div class="btnrow"><a href="#/model/' + encodeURIComponent(t.id) + '"><button>🧍 3D 자세·근육 보기</button></a></div>';

    app.innerHTML = html;
    bindTabs(app);

    var hideToggle = document.getElementById("hideToggle");
    var nameEl = document.getElementById("muscleName");
    hideToggle.addEventListener("click", function () {
      nameEl.classList.toggle("blurred");
      hideToggle.textContent = nameEl.classList.contains("blurred") ? "👁 이름 보기" : "🙈 이름 가리고 암기 연습";
    });
    nameEl.classList.add("blurred");
    hideToggle.textContent = "👁 이름 보기";
    nameEl.addEventListener("click", function () { nameEl.classList.remove("blurred"); });

    app.querySelectorAll(".f3-img").forEach(function (img) {
      img.addEventListener("click", function () { img.classList.toggle("zoomed"); });
    });
  }

  function bindTabs(root) {
    var tabs = root.querySelectorAll(".tab");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        var key = tab.dataset.tab;
        root.querySelectorAll(".tab").forEach(function (x) { x.classList.toggle("active", x === tab); });
        root.querySelectorAll(".tabpanel").forEach(function (p) {
          p.style.display = (p.dataset.panel === key) ? "" : "none";
        });
      });
    });
  }

  // ---------- 퀴즈 ----------
  function renderQuizStart(app, crumb) {
    crumb.innerHTML = "<b>퀴즈</b>";
    var html = "";
    html += '<div class="card">';
    html += '<h2>체인 복습 퀴즈</h2>';
    html += '<p class="muted">검사·의심근육·테크닉 카드에서 자동으로 출제됩니다. 오답은 오답노트에 자동 저장돼요.</p>';
    html += '<div class="btnrow">';
    html += '<button data-n="10">10문제</button>';
    html += '<button class="secondary" data-n="20">20문제</button>';
    html += '<button class="secondary" data-n="' + QUIZ_POOL.length + '">전체(' + QUIZ_POOL.length + '문제)</button>';
    html += '</div></div>';
    app.innerHTML = html;
    app.querySelectorAll("button[data-n]").forEach(function (b) {
      b.addEventListener("click", function () {
        location.hash = "#/quizrun/" + b.dataset.n;
      });
    });
  }

  function renderQuizRun(app, crumb, nStr) {
    var n = Math.min(parseInt(nStr, 10) || 10, QUIZ_POOL.length);
    var session = sample(QUIZ_POOL, n);
    var idx = 0, correctCount = 0, wrongItems = [];

    crumb.innerHTML = "<b>퀴즈 진행 중</b>";

    function renderQuestion() {
      if (idx >= session.length) return renderResult();
      var q = session[idx];
      var html = "";
      html += '<div class="progress"><div style="width:' + Math.round(100 * idx / session.length) + '%"></div></div>';
      html += '<div class="muted" style="font-size:12px;margin-bottom:8px">' + (idx + 1) + ' / ' + session.length + '</div>';
      html += '<div class="card"><b style="white-space:pre-wrap">' + esc(q.prompt) + '</b></div>';
      q.choices.forEach(function (c, i) {
        html += '<button class="quiz-choice" data-i="' + i + '">' + esc(truncate(c, 140)) + '</button>';
      });
      app.innerHTML = html;

      app.querySelectorAll(".quiz-choice").forEach(function (btn) {
        btn.addEventListener("click", function () {
          var chosen = q.choices[parseInt(btn.dataset.i, 10)];
          var correct = chosen === q.answer;
          app.querySelectorAll(".quiz-choice").forEach(function (b2) {
            b2.disabled = true;
            if (b2.textContent === truncate(q.answer, 140)) b2.classList.add("correct");
          });
          if (!correct) btn.classList.add("wrong");
          recordAttempt(q.cardId, q.cardTitle, q.kind, correct);
          if (correct) correctCount++; else wrongItems.push(q);
          setTimeout(function () { idx++; renderQuestion(); }, 700);
        });
      });
    }

    function renderResult() {
      var pct = session.length ? Math.round(100 * correctCount / session.length) : 0;
      var html = "";
      html += '<div class="card" style="text-align:center">';
      html += '<div class="stat"><b>' + pct + '%</b><small>정답률 (' + correctCount + '/' + session.length + ')</small></div>';
      html += '</div>';
      if (wrongItems.length) {
        html += '<div class="section-title">틀린 문제 다시보기</div>';
        wrongItems.forEach(function (q) {
          var link = q.kind === "assessment" ? "#/assessment/" + encodeURIComponent(q.cardId) : "#/technique/" + encodeURIComponent(q.cardId);
          html += '<a href="' + link + '"><div class="card"><div class="muted" style="font-size:12px">' + esc(truncate(q.prompt, 60)) + '</div>' +
            '<b>정답: ' + esc(q.answer) + '</b></div></a>';
        });
      }
      html += '<div class="btnrow"><a href="#/quiz"><button>다시 풀기</button></a><a href="#/home"><button class="secondary">홈으로</button></a></div>';
      app.innerHTML = html;
    }

    renderQuestion();
  }

  // ---------- 오답노트 ----------
  function renderReview(app, crumb) {
    crumb.innerHTML = "<b>오답노트 · 약점 관리</b>";
    var wl = weaknessList().filter(function (w) { return w.seen > 0; });
    wl.sort(function (a, b) { return a.acc - b.acc || b.wrong - a.wrong; });
    var html = "";
    if (!wl.length) {
      html = '<div class="empty">아직 퀴즈 기록이 없습니다.<br><br><a href="#/quiz"><button>퀴즈 시작하기</button></a></div>';
    } else {
      wl.forEach(function (w) {
        var link = w.kind === "assessment" ? "#/assessment/" + encodeURIComponent(w.id) : "#/technique/" + encodeURIComponent(w.id);
        var pct = Math.round(w.acc * 100);
        html += '<a href="' + link + '"><div class="card hp-row">';
        html += '<div><b>' + esc((w.title + "").split("/")[0].trim()) + '</b><br><span class="muted" style="font-size:12px">' + (w.kind === "assessment" ? "검사카드" : "테크닉카드") + '</span></div>';
        html += '<div style="text-align:right"><b style="color:' + (pct < 50 ? "#d9534f" : pct < 80 ? "#e0a83a" : "#3a9d5f") + '">' + pct + '%</b><br><span class="muted" style="font-size:11px">' + w.correct + '/' + w.seen + '</span></div>';
        html += '</div></a>';
      });
      html += '<div class="btnrow"><button class="ghost" id="resetBtn">기록 초기화</button></div>';
    }
    app.innerHTML = html;
    var resetBtn = document.getElementById("resetBtn");
    if (resetBtn) resetBtn.addEventListener("click", function () {
      if (confirm("모든 퀴즈 기록을 초기화할까요?")) { localStorage.removeItem(LS_KEY); renderReview(app, crumb); }
    });
  }

  // ---------- 검색 ----------
  function renderSearch(app, crumb, q) {
    crumb.innerHTML = '<b>검색: ' + esc(q) + '</b>';
    var n = normalize(q);
    var results = [];
    DATA.assessments.forEach(function (a) {
      var hay = normalize((a.frontmatter["검사명"] || "") + JSON.stringify(a.sections));
      if (hay.indexOf(n) >= 0) results.push({ kind: "assessment", card: a });
    });
    DATA.techniques.forEach(function (t) {
      var hay = normalize((t.frontmatter["근육명"] || "") + JSON.stringify(t.sections));
      if (hay.indexOf(n) >= 0) results.push({ kind: "technique", card: t });
    });
    var html = "";
    if (!results.length) {
      html = '<div class="empty">검색 결과가 없습니다.</div>';
    } else {
      results.forEach(function (r) {
        var name = (r.card.frontmatter[r.kind === "assessment" ? "검사명" : "근육명"] || r.card.title).split("/")[0].trim();
        var link = r.kind === "assessment" ? "#/assessment/" + encodeURIComponent(r.card.id) : "#/technique/" + encodeURIComponent(r.card.id);
        html += '<a href="' + link + '"><div class="searchresult"><b>' + esc(name) + '</b> <span class="pill">' + (r.kind === "assessment" ? "검사" : "테크닉") + '</span></div></a>';
      });
    }
    app.innerHTML = html;
  }

  // ---------- 초기화 ----------
  function init() {
    function getJSON(u) { return fetch(u).then(function (r) { return r.json(); }).catch(function () { return null; }); }
    Promise.all([getJSON("data.json"), getJSON("viz_data.json"), getJSON("muscle_map.json")])
      .then(function (res) {
      DATA = res[0];
      VIZ = res[1];
      MMAP = res[2];
      buildIndices();
      buildQuizPool();
      window.addEventListener("hashchange", route);
      route();

      var searchInput = document.getElementById("searchInput");
      var searchTimer;
      searchInput.addEventListener("input", function () {
        clearTimeout(searchTimer);
        var v = searchInput.value.trim();
        searchTimer = setTimeout(function () {
          if (v) { location.hash = "#/search/" + encodeURIComponent(v); }
        }, 350);
      });
      searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && searchInput.value.trim()) {
          location.hash = "#/search/" + encodeURIComponent(searchInput.value.trim());
        }
      });
    }).catch(function (err) {
      document.getElementById("app").innerHTML = '<div class="empty">데이터를 불러오지 못했습니다: ' + esc(err.message) + '</div>';
    });

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
