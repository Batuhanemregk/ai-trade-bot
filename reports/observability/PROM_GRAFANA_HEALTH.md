# Prometheus & Grafana Sağlık Kontrolü
**Tarih:** 2025-10-21  
**Durum:** Hazır (Docker başlatılmayı bekliyor)

## 📋 Durum (Güncel)

**Prometheus:** ✅ Running (Docker container UP)  
**Grafana:** ✅ Running (Docker container UP)  
**Bot Metrics:** ⏳ Bot başlatılacak (port 8000)

## 🚀 Başlatma Komutları

### Docker Compose ile (Önerilen)
```bash
# Monitoring stack'i başlat
cd monitoring/
docker-compose up -d

# Durum kontrolü
docker-compose ps

# Logları izle
docker-compose logs -f prometheus grafana
```

### Manuel Port Kontrolü
```powershell
# Bot metrics (port 8000)
Test-NetConnection -ComputerName localhost -Port 8000

# Prometheus (port 9090)
Test-NetConnection -ComputerName localhost -Port 9090

# Grafana (port 3000)
Test-NetConnection -ComputerName localhost -Port 3000
```

## ✅ Sağlık Kontrol Checklist'i

### 1. Bot Metrics Endpoint
```bash
# HTTP GET test
curl http://localhost:8000/metrics

# Beklenen çıktı (örnek)
aibot_llm_requests_total{status="2xx"} 10
aibot_llm_cost_usd_total 0.0015
aibot_news_items_total{sent_to_llm="true"} 30
aibot_news_items_total{sent_to_llm="false"} 90
aibot_news_digest_hits_total 30
```

**PASS Kriteri:**
- HTTP 200 OK
- `aibot_*` metrikler görünür
- Değerler artıyor (bot çalışıyor)

### 2. Prometheus Targets
```bash
# Targets durumu
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job, health}'

# Beklenen çıktı
{
  "job": "aibot",
  "health": "up"
}
```

**PASS Kriteri:**
- Target `aibot` UP
- Last scrape başarılı
- Scrape duration < 1s

### 3. Prometheus Queries
```bash
# Test queries
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=rate(aibot_llm_requests_total[5m])' | jq '.data.result'

curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=increase(aibot_news_digest_hits_total[1h])' | jq '.data.result'

curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=sum(aibot_llm_cost_usd_total)' | jq '.data.result'
```

**PASS Kriteri:**
- Queries veri döndürüyor
- Değerler mantıklı (>= 0)

### 4. Grafana Health
```bash
# Health check
curl http://localhost:3000/api/health

# Beklenen çıktı
{
  "database": "ok",
  "version": "...",
  "commit": "..."
}
```

**PASS Kriteri:**
- HTTP 200 OK
- database: "ok"

### 5. Grafana Datasource
```bash
# Datasource listesi
curl -u admin:admin123 http://localhost:3000/api/datasources | jq '.[] | {name, type, url}'

# Prometheus datasource test
curl -u admin:admin123 -X POST http://localhost:3000/api/datasources/proxy/1/api/v1/query \
  -d 'query=up'
```

**PASS Kriteri:**
- Prometheus datasource mevcut
- Proxy query çalışıyor

## 📊 Başlatılınca Çalıştırılacak Kontroller

### Quick Health Check Script
```powershell
# healthcheck.ps1
$endpoints = @(
    @{Name="Bot Metrics"; URL="http://localhost:8000/metrics"},
    @{Name="Prometheus API"; URL="http://localhost:9090/api/v1/status/config"},
    @{Name="Grafana Health"; URL="http://localhost:3000/api/health"}
)

foreach ($ep in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri $ep.URL -TimeoutSec 5 -UseBasicParsing
        Write-Host "✅ $($ep.Name): UP" -ForegroundColor Green
    } catch {
        Write-Host "❌ $($ep.Name): DOWN" -ForegroundColor Red
    }
}
```

### Prometheus PromQL Test Queries
```promql
# 1. LLM request rate (per 5 minutes)
rate(aibot_llm_requests_total[5m])

# 2. News digest hits (last hour)
increase(aibot_news_digest_hits_total[1h])

# 3. Total LLM cost
sum(aibot_llm_cost_usd_total)

# 4. News items breakdown
sum by(sent_to_llm) (increase(aibot_news_items_total[1h]))

# 5. Budget status
aibot_llm_budget_trips_total
```

## 🎯 PASS/FAIL Kriterleri

### ✅ PASS (Tümü Sağlanmalı)
- [ ] Bot metrics endpoint (8000) erişilebilir
- [ ] Prometheus (9090) UP ve scraping
- [ ] Grafana (3000) UP ve datasource bağlı
- [ ] `aibot_*` metrikleri görünür ve artıyor
- [ ] PromQL sorguları veri döndürüyor
- [ ] No 404/500 errors

### ❌ FAIL (Herhangi Biri)
- [ ] Endpoint'ler erişilemez
- [ ] Prometheus target DOWN
- [ ] Grafana datasource error
- [ ] Metrikler görünmüyor veya 0
- [ ] Query timeout / errors

## 🔧 Troubleshooting

### Problem: Port already in use
```bash
# Port kullanımını kontrol et
netstat -ano | findstr :8000
netstat -ano | findstr :9090
netstat -ano | findstr :3000

# Process'i durdur
Stop-Process -Id <PID> -Force
```

### Problem: Docker not running
```bash
# Docker Desktop başlat
# Windows: Start menu → Docker Desktop

# Durum kontrolü
docker version
docker-compose version
```

### Problem: Prometheus can't scrape bot
```bash
# Bot'un IP/port'unu kontrol et
# prometheus.yml targets
cat monitoring/prometheus.yml | grep -A 5 "aibot"

# Network connectivity
curl http://host.docker.internal:8000/metrics  # Docker'dan
curl http://localhost:8000/metrics             # Host'tan
```

---

## 🔍 Gerçek Durum Kontrolü (2025-10-21 22:25 UTC)

### Prometheus Targets (http://localhost:9090/api/v1/targets)

```json
{
  "activeTargets": [
    {
      "job": "ai-trading-bot",
      "health": "down",  // ← Bot henüz başlamadı
      "lastError": "connection refused",
      "scrapeUrl": "http://host.docker.internal:8000/metrics",
      "scrapeInterval": "10s"
    },
    {
      "job": "prometheus",
      "health": "up",  // ← Prometheus kendisi UP
      "lastError": "",
      "scrapeInterval": "15s"
    }
  ]
}
```

**Analiz:**
- ✅ Prometheus config doğru (target var)
- ✅ Scrape ayarları doğru (10s interval)
- ⏳ Bot target DOWN (bot başlamadı, port 8000 kapalı)
- ✅ Self-scraping UP (Prometheus kendi metriklerini topluyor)

### Grafana Health (http://localhost:3000/api/health)

```json
{
  "database": "ok",
  "version": "11.4.0"
}
```

**Analiz:**
- ✅ Grafana UP ve healthy
- ✅ Database bağlantısı OK
- ✅ Web UI erişilebilir (http://localhost:3000)
- ⏳ Datasource test bot başlayınca yapılacak

## 📊 Bot Başlatılınca Görünecek Metrikler

### Expected aibot_* Metrics (bot başladığında)

```
# /metrics endpoint'ten beklenen çıktı
aibot_llm_requests_total{status="2xx",model="gpt-5-nano"} 0
aibot_llm_cost_usd_total 0.0
aibot_news_items_total{sent_to_llm="true"} 0
aibot_news_items_total{sent_to_llm="false"} 0
aibot_news_digest_hits_total 0
aibot_llm_budget_trips_total{type="tokens"} 0
aibot_llm_budget_trips_total{type="usd"} 0
```

### PromQL Test Queries (bot başladıktan 30 dk sonra)

#### 1. LLM Request Rate
```promql
rate(aibot_llm_requests_total[5m])
# Expected: 0.01-0.03 requests/sec (digest cache sayesinde düşük)
```

#### 2. Digest Hits (Last Hour)
```promql
increase(aibot_news_digest_hits_total[1h])
# Expected: ~20-30 hits (70% hit rate)
```

#### 3. Total LLM Cost
```promql
sum(aibot_llm_cost_usd_total)
# Expected: $0.0005-0.0015 (30 dk test)
```

#### 4. News Items Breakdown
```promql
sum by(sent_to_llm) (increase(aibot_news_items_total[1h]))
# Expected: 
# {sent_to_llm="false"} ~80  (digest hits)
# {sent_to_llm="true"} ~30   (LLM'e gönderilen)
```

---

**Not:** Bot başlatıldığında target "down" → "up" olacak ve metrikler toplanmaya başlayacak.

**Durum:** ✅ Monitoring stack hazır, bot başlatılmayı bekliyor
