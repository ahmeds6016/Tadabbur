#!/bin/bash

TOKEN="eyJhbGciOiJSUzI1NiIsImtpZCI6IjlkMjEzMGZlZjAyNTg3ZmQ4ODYxODg2OTgyMjczNGVmNzZhMTExNjUiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vdGFmc2lyLXNpbXBsaWZpZWQtNmIyNjIiLCJhdWQiOiJ0YWZzaXItc2ltcGxpZmllZC02YjI2MiIsImF1dGhfdGltZSI6MTc2MDc1Mjc5NywidXNlcl9pZCI6InNnVlRKNmgyREZlUXNwRXdUTTlsaURDNkZvcTEiLCJzdWIiOiJzZ1ZUSjZoMkRGZVFzcEV3VE05bGlEQzZGb3ExIiwiaWF0IjoxNzYwOTI4MTE1LCJleHAiOjE3NjA5MzE3MTUsImVtYWlsIjoidGVzdHRlc3R0ZXN0MTIzQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJ0ZXN0dGVzdHRlc3QxMjNAZ21haWwuY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoicGFzc3dvcmQifX0.l12MfeTD_0Di5x7SkVn_gYlAYujHGU1VbOxjE7QSaGownlUkz528cdoChMceHQFAOh7w5gcHOQ4ALK20AH1JKITljgFj_6DSzJJ183zetfsbDvajgck_gT6sQhYbJIZBK6wTVCI1mJeZpfTGiQlqvTg5KNd-XuaimWDg0iDupvVyKayrDsSyUCHaRKDLOTTnCVOENTGfzdjw7AQdnjlyWZBSOeYd-K_vaWV5sOq5itB4v63HmbjsCeAxuLUJOliigvm62QfbvkEmDdxLI0zOU0d64qhC20WhXdZQw1RnJeVK0PTFQymxKp2GEL9S5V8jFhecIeTMasHStP0ddodZmQ"

test_query() {
  local query=$1
  local test_num=$2

  echo "=== Test $test_num for $query ==="
  RESPONSE=$(curl -s -X POST 'https://tafsir-backend-612616741510.us-central1.run.app/tafsir' \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"query\": \"$query\", \"approach\": \"tafsir\"}")

  echo "$RESPONSE" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    answer = d.get('answer', '')
    if answer and 'No relevant information found' in answer:
        print('❌ FAILED: No relevant information found')
    elif answer and len(answer) > 100:
        print(f'✅ SUCCESS: Answer length = {len(answer)} chars')
    else:
        print(f'⚠️  UNKNOWN: {str(answer[:100] if answer else d.get(\"error\", \"No answer\"))}')
except Exception as e:
    print(f'ERROR: {e}')
"
  echo ""
}

echo "========================================="
echo "Testing 2:255 (5 times)"
echo "========================================="
for i in {1..5}; do
  test_query "2:255" "$i"
  sleep 1
done

echo ""
echo "========================================="
echo "Testing 2:254 (3 times)"
echo "========================================="
for i in {1..3}; do
  test_query "2:254" "$i"
  sleep 1
done

echo ""
echo "========================================="
echo "Testing 24:35 (3 times)"
echo "========================================="
for i in {1..3}; do
  test_query "24:35" "$i"
  sleep 1
done
