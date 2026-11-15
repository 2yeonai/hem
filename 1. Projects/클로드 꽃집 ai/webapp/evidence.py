"""Conservative explicit delivery extraction and exact source excerpts."""
import re
from datetime import date

PATTERNS = {
 'delivery_date': r'(?:배송일|배송날짜)\s*[:：]\s*(\d{4}-\d{2}-\d{2})',
 'delivery_time': r'(?:배송시간|배송시각)\s*[:：]\s*(\d{1,2}:\d{2})',
 'delivery_address': r'(?:배송주소|배송지|주소)\s*[:：]\s*([^;\n]+)',
 'delivery_phone': r'(?:배송연락처|연락처|전화번호)\s*[:：]\s*([\d -]{9,20})',
}


def enrich(result, text):
    result = dict(result)
    fields = dict(result.get('order_draft') or {})
    confidence = dict(result.get('field_confidence') or {})
    evidence = dict(result.get('field_evidence') or {})
    sources = dict(result.get('field_sources') or {})
    for key, pattern in PATTERNS.items():
        matches = list(re.finditer(pattern, text))
        if len(matches) == 1:
            fields[key] = matches[0].group(1).strip()
            evidence[key] = matches[0].group(0)
            confidence[key] = .95
    for key, value in fields.items():
        excerpt = evidence.get(key)
        # A model's explanation is not source evidence: accept exact excerpts only.
        if not isinstance(excerpt, str) or not excerpt.strip() or excerpt not in text:
            excerpt = str(value) if value is not None and str(value) in text else None
        evidence[key] = excerpt
        try: score = max(0., min(1., float(confidence.get(key, 0))))
        except (ValueError, TypeError): score = 0.
        confidence[key] = score if excerpt else 0.
        sources[key] = '원문 직접 대조' if excerpt else '원문 근거 확인 필요'
    result.update(order_draft=fields, field_confidence=confidence,
                  field_evidence=evidence, field_sources=sources)
    return result
