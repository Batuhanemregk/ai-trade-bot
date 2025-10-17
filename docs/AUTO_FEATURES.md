# 🚀 **OTOMATİK AKTİF OLAN ÖZELLİKLER**

> **Sistem başlarken ekstra komut yazmana gerek yok!**

---

## ✅ **EVET, HEPSİ OTOMATİK AKTİF!**

Sistem başladığında (`python -m infrastructure.scheduler_runner`), 4 özellik **otomatik** olarak devreye girer:

---

## **#1: Ayar Dosyası Kontrolü (Config Validation)**

### **Manuel Kontrol (İsteğe bağlı):**
```bash
python scripts/validate_config.py
```

### **Otomatik Kontrol (Sistem başlarken):**
```bash
python -m infrastructure.scheduler_runner
# ↓ Sistem başlarken otomatik çalışır
# ✅ Configuration validated successfully
```

**Ne zaman çalışır?**
- ✅ Scheduler başlarken **otomatik**
- ✅ `python scripts/validate_config.py` ile **manuel**

**Yanlış ayar varsa ne olur?**
```
❌ Configuration validation failed! Fix errors in policy.yaml
→ Sistem başlamaz!
→ Hataları düzeltmen gerekir
```

**Örnek:**
```
Sen: python -m infrastructure.scheduler_runner

Sistem: 
  [CHECK] Required Files ✅
  [CHECK] Loading Policy ✅
  [CHECK] Pydantic Model Validation ✅
  [CHECK] JSON Schema Validation ✅
  [CHECK] Business Rules Validation ✅
  
  ✅ Configuration validated successfully
  ✅ Scheduler initialized successfully
  
→ Ayarlar doğru, sistem başladı!
```

---

## **#2: Karar Kayıt Defteri (Decision Logger)**

### **Otomatik Aktif:**
```
Sistem başlarken:
✅ DecisionLogger initialized: logs/decisions

Her 15 dakikada:
→ Trading analizi çalışır
→ Her karar otomatik loglanır
→ logs/decisions/decisions_2025-10-10.jsonl
```

**Manuel komut gerekmez!**

**Ne zaman çalışır?**
- ✅ Her trading kararında **otomatik**
- ✅ Her 15 dakikada bir **otomatik**
- ✅ Hiçbir şey yapman gerekmez

**Nerede bulunur?**
```bash
# Bugünkü kararlar
logs/decisions/decisions_2025-10-10.jsonl

# Geriye dönük analiz (manuel)
python scripts/replay_decisions.py
```

---

## **#3: Acil Fren Sistemi (Circuit Breaker)**

### **Otomatik Aktif:**
```
Sistem başlarken:
✅ Circuit Breaker initialized (state=normal)

Her 1 dakikada (risk_monitor job):
→ Günlük zarar kontrol edilir
→ Art arda kayıplar izlenir
→ Gerekirse otomatik durdurur
```

**Manuel komut gerekmez!**

**Ne zaman çalışır?**
- ✅ Her dakika risk kontrolü **otomatik**
- ✅ Günlük zarar %25 → **Otomatik durdur**
- ✅ 3 art arda kayıp → **Otomatik 24h mola**

**Manuel kontroller (isteğe bağlı):**
```bash
/breaker  # Durum kontrolü
/stop     # Manuel durdur
/pause 24 # Manuel mola
/resume   # Devam et
```

---

## **#4: Gizli Bilgi Koruma (Log Redaction)**

### **Otomatik Aktif:**
```
Sistem başlarken:
✅ Secure logging initialized (with API key redaction)

Her log yazıldığında:
→ API keys otomatik maskelenir: abc1***
→ Secrets otomatik maskelenir: my-s***
→ Tokens otomatik maskelenir: 1234***
```

**Manuel komut gerekmez!**
**Her zaman aktif!**

**Ne zaman çalışır?**
- ✅ Her log yazıldığında **otomatik**
- ✅ Console'da **otomatik**
- ✅ Log dosyalarında **otomatik**
- ✅ Hiçbir şey yapman gerekmez

**Test:**
```bash
# Log dosyasını aç
tail logs/main.log

# API key'i ara
grep "api_key" logs/main.log

# Göreceğin:
api_key=abc1***  (maskelenmiş ✅)
```

---

## 🎯 **ÖZET TABLO**

| Özellik | Otomatik Aktif? | Manuel Kontrol Gerekir mi? |
|---------|-----------------|----------------------------|
| **Config Validation** | ✅ Başlangıçta | ❌ İsteğe bağlı |
| **Decision Logger** | ✅ Her 15 dakika | ❌ İsteğe bağlı (replay için) |
| **Circuit Breaker** | ✅ Her dakika | ❌ İsteğe bağlı (manuel kontrol için) |
| **Log Redaction** | ✅ Her zaman | ❌ Asla |

---

## 💡 **BASIT AÇIKLAMA**

### **Senaryo: Sistemi Başlattın**
```bash
python -m infrastructure.scheduler_runner
```

**Arka planda otomatik olarak:**

1. **Config Validation:**
   ```
   ✅ Ayarları kontrol et
   ✅ Yanlış bir şey var mı bak
   ✅ Yoksa devam et, varsa durdur
   ```

2. **Decision Logger:**
   ```
   ✅ Defter aç (logs/decisions/)
   ✅ Her 15 dakika kararları yaz
   ✅ "Neden bu işlemi yaptık?" kaydet
   ```

3. **Circuit Breaker:**
   ```
   ✅ Risk sistemi hazır
   ✅ Her dakika kontrol et
   ✅ Sorun varsa otomatik durdur
   ```

4. **Log Redaction:**
   ```
   ✅ Her logda API key'leri maskele
   ✅ Kimse hassas bilgileri göremesin
   ✅ Güvenli paylaşım için hazır
   ```

**Sen hiçbir şey yapmadın, hepsi otomatik! 🎉**

---

## ❓ **SORULAR & CEVAPLAR**

### **S: `python scripts/validate_config.py` yazmam gerekir mi?**
**C:** Hayır, **sistem başlarken otomatik çalışır**. Ama önceden kontrol etmek istersen manuel çalıştırabilirsin.

### **S: Decision logger'ı açmam gerekir mi?**
**C:** Hayır, **her 15 dakikada otomatik çalışır**. Sadece geçmişe bakmak için replay script'i kullan.

### **S: Circuit breaker'ı başlatmam gerekir mi?**
**C:** Hayır, **sistem başlarken otomatik başlar**. Risk kontrolü her dakika otomatik yapılır.

### **S: Log redaction'ı aktif etmem gerekir mi?**
**C:** Hayır, **her zaman aktif**. Log yazdığında otomatik maskelenir.

### **S: Sistem çalışırken özellikler kapanır mı?**
**C:** Hayır, **sistem kapanana kadar hepsi aktif kalır**.

### **S: Restart'ta ne olur?**
**C:** Sistem tekrar başladığında **hepsi otomatik tekrar aktif olur**.

---

## ✅ **SONUÇ**

**Tek yapman gereken:**
```bash
python -m infrastructure.scheduler_runner
```

**Gerisi otomatik!** 🚀

- ✅ Config kontrol edilir
- ✅ Kararlar loglanır
- ✅ Riskler izlenir
- ✅ Bilgiler korunur

**Hiçbir ekstra komut gerekmez!**

---

**Son Güncelleme:** 2025-10-10  
**Version:** 1.0.0

