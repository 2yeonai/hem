// 퀴즈 풀 검증 스크립트 — app/app.js 의 buildQuizPool/parseArrowField/firstLine/sample/shuffle 로직을
// 그대로 재현해 app/data.json(93장 반영본)에 대해 실행한다.
// 실행: node scripts/validate_quiz.js
"use strict";

const fs = require("fs");
const path = require("path");

const DATA_PATH = path.join(__dirname, "..", "app", "data.json");
const DATA = JSON.parse(fs.readFileSync(DATA_PATH, "utf-8"));

// ---- app.js 에서 그대로 복사한 유틸 함수 ----
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

// ---- buildQuizPool 그대로 재현 ----
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
      kind: "assessment", type: "A", cardId: a.id, cardTitle: a.frontmatter["검사명"] || a.title,
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
      kind: "assessment", type: "B", cardId: a.id, cardTitle: a.frontmatter["검사명"] || a.title,
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
      kind: "technique", type: "C", cardId: t.id, cardTitle: t.frontmatter["근육명"] || t.title,
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
      kind: "technique", type: "D", cardId: t.id, cardTitle: t.frontmatter["근육명"] || t.title,
      prompt: '다음 핵심 한 줄 설명에 해당하는 근육은?\n"' + line + '"',
      choices: choices, answer: correct
    });
  });

  return pool;
}

// ---- 검증 ----
function main() {
  var pool = buildQuizPool();
  var byType = {};
  var errors = [];

  pool.forEach(function (q, idx) {
    byType[q.type] = (byType[q.type] || 0) + 1;
    if (!Array.isArray(q.choices) || q.choices.length !== 4) {
      errors.push("choices 길이 이상 (type=" + q.type + ", idx=" + idx + ", cardId=" + q.cardId + "): len=" + (q.choices && q.choices.length));
    }
    if (q.choices.indexOf(q.answer) < 0) {
      errors.push("answer가 choices에 없음 (type=" + q.type + ", idx=" + idx + ", cardId=" + q.cardId + "): answer=" + JSON.stringify(q.answer));
    }
    // 중복 choice 체크 (선택지 4개 중 실질적으로 겹치는 문구가 있으면 퀴즈 품질 이슈)
    var uniq = new Set(q.choices);
    if (uniq.size !== q.choices.length) {
      errors.push("choices 내 중복 존재 (type=" + q.type + ", idx=" + idx + ", cardId=" + q.cardId + "): " + JSON.stringify(q.choices));
    }
  });

  console.log("=== 유형별 생성 문제 수 ===");
  ["A", "B", "C", "D"].forEach(function (t) {
    console.log("  " + t + ": " + (byType[t] || 0));
  });
  console.log("  합계: " + pool.length);

  console.log("\n=== choices/answer 무결성 오류 ===");
  console.log("  오류 개수: " + errors.length);
  errors.slice(0, 20).forEach(function (e) { console.log("  - " + e); });

  // B유형: parseArrowField 파싱 결과에 괄호 설명 잔존 여부 체크 ("카드없음" 등 노출)
  console.log("\n=== B유형 parseArrowField 파싱 품질 체크 ===");
  var leaked = [];
  var stringFormatCount = 0, arrayFormatCount = 0;
  DATA.assessments.forEach(function (a) {
    var raw = a.frontmatter["의심근육→"];
    if (raw == null) return;
    if (Array.isArray(raw)) arrayFormatCount++;
    else if (typeof raw === "string") stringFormatCount++;
    var parsed = parseArrowField(raw);
    parsed.forEach(function (m) {
      if (/[()（）]/.test(m) || /카드없음/.test(m)) {
        leaked.push({ cardId: a.id, raw: raw, parsed: m });
      }
    });
  });
  console.log("  원본 포맷: 배열(list) " + arrayFormatCount + "건, 문자열(string, '[...]') " + stringFormatCount + "건");
  console.log("  괄호/부가설명 잔존(파싱 깨짐) 사례: " + leaked.length + "건");
  leaked.slice(0, 10).forEach(function (l) {
    console.log("  - " + l.cardId + ": raw=" + JSON.stringify(l.raw) + " -> parsed=" + JSON.stringify(l.parsed));
  });

  // DNF근력검사 케이스 특정 확인 (문자열로 감싸인 '[...]' 포맷 대표 예시)
  console.log("\n=== 특정 케이스 확인: 검사_DNF근력검사 ===");
  var dnf = DATA.assessments.find(function (a) { return /DNF/.test(a.id) && /DNF근력검사|DNF/.test(String(a.frontmatter["검사명"] || a.title)); });
  if (dnf) {
    console.log("  id=" + dnf.id);
    console.log("  raw=" + JSON.stringify(dnf.frontmatter["의심근육→"]));
    console.log("  parsed=" + JSON.stringify(parseArrowField(dnf.frontmatter["의심근육→"])));
  } else {
    console.log("  (DNF근력검사 카드 못 찾음)");
  }

  // B유형: pool2 < 3 이라 문제가 생성 안 되는 검사 카드 개수
  console.log("\n=== B유형: 의심근육은 있지만 오답 후보(pool2) 3개 미만이라 제외된 검사 ===");
  var excluded = [];
  DATA.assessments.forEach(function (a) {
    var suspects = parseArrowField(a.frontmatter["의심근육→"]);
    if (!suspects.length) return; // 애초에 의심근육 없음(다른 사유)
    var pool2 = [];
    DATA.assessments.forEach(function (x) {
      if (x.id === a.id) return;
      parseArrowField(x.frontmatter["의심근육→"]).forEach(function (m) { if (suspects.indexOf(m) < 0) pool2.push(m); });
    });
    pool2 = Array.from(new Set(pool2));
    if (pool2.length < 3) excluded.push({ id: a.id, suspects: suspects, pool2size: pool2.length });
  });
  console.log("  건수: " + excluded.length + " / 의심근육 있는 검사 " + DATA.assessments.filter(function(a){return parseArrowField(a.frontmatter["의심근육→"]).length;}).length + "건 중");
  excluded.forEach(function (e) { console.log("  - " + e.id + " (suspects=" + JSON.stringify(e.suspects) + ", pool2=" + e.pool2size + ")"); });

  // 의심근육 필드 자체가 비어서 B유형에서 아예 빠지는 검사
  console.log("\n=== B유형: 의심근육→ 필드가 비어 있어(파싱 결과 0개) 애초에 제외된 검사 ===");
  var noSuspects = DATA.assessments.filter(function (a) { return parseArrowField(a.frontmatter["의심근육→"]).length === 0; });
  console.log("  건수: " + noSuspects.length + " / 전체 " + DATA.assessments.length + "건 중");
  noSuspects.forEach(function (a) { console.log("  - " + a.id + " raw=" + JSON.stringify(a.frontmatter["의심근육→"])); });

  // A유형: 양성 판단 섹션 없어 제외된 검사
  console.log("\n=== A유형: '양성 판단' 섹션 없어 제외된 검사 ===");
  var noPositive = DATA.assessments.filter(function (a) { return !firstLine(a.sections["양성 판단"]); });
  console.log("  건수: " + noPositive.length);
  noPositive.forEach(function (a) { console.log("  - " + a.id); });

  // C/D: 섹션 없어 제외된 테크닉
  console.log("\n=== C유형: '이 사람에게 해!' 섹션 없어 제외된 테크닉 ===");
  var noC = DATA.techniques.filter(function (t) { return !firstLine(t.sections["이 사람에게 해!"]); });
  console.log("  건수: " + noC.length);
  noC.forEach(function (t) { console.log("  - " + t.id); });

  console.log("\n=== D유형: '핵심 한 줄' 섹션 없어 제외된 테크닉 ===");
  var noD = DATA.techniques.filter(function (t) { return !firstLine(t.sections["핵심 한 줄"]); });
  console.log("  건수: " + noD.length);
  noD.forEach(function (t) { console.log("  - " + t.id); });

  console.log("\n=== 최종 판정 ===");
  console.log(errors.length === 0 ? "PASS: choices/answer 무결성 문제 없음" : "FAIL: 위 오류 목록 참고");
}

main();
