# config.py - Tüm Ayarlar Tek Yerde


# --- Video / Genel ---
DEFAULT_FPS = 30.0                # video bilinmeyen FPS verirse bu kullanılır

# --- YOLO Araç Tespiti ---
CONFIDENCE_THRESHOLD = 0.45       # bu değerin altındaki tespitler atılır
IOU_THRESHOLD = 0.45
DEVICE = "cpu"                    # GPU'nuz yoksa "cpu" kalsın. Colab'da GPU açıksa "cuda" yapabilirsiniz.

VEHICLE_CLASSES = [0, 1, 2, 3]    

# --- DeepSORT Takip ---
TRACK_MAX_AGE = 30
TRACK_N_INIT = 3

# --- Şerit / Hız Hesabı ---
REAL_LANE_WIDTH_METERS = 3.5      # TR karayolu standart şerit genişliği
MIN_VALID_LANE_WIDTH_PX = 50      # bundan dar şerit ölçümü güvenilmez sayılır
MAX_VALID_LANE_WIDTH_PX = 500     # bundan geniş şerit ölçümü güvenilmez sayılır

# Şerit çizgisi görünmüyorsa (örn. otopark, iç mekan, şerit boyası silik) sistem
# km/h hesaplayamaz hale gelir. Bunu önlemek için burada SABİT bir ölçek
# tanımlıyoruz: görüntüde kaç piksel = kaç metre. Bunu kendi sahnenize göre
# AYARLAMANIZ gerekir, aksi halde hız değerleri gerçekçi olmaz.
#
# Nasıl ölçülür: Videoda gerçek dünyada uzunluğunu bildiğiniz bir şey bulun
# (örn. bir park çizgisi: genelde 5 metre, bir araç kapısı: ~1 metre,
# bir kapı genişliği: ~1-1.2 metre). O nesnenin görüntüde kapladığı piksel
# sayısını ölçüp aşağıdaki formülü kullandık:
#   FALLBACK_PIXELS_PER_METER = piksel_uzunluk / gerçek_metre_uzunluk
USE_FALLBACK_SCALE_WHEN_NO_LANE = True   # şerit yoksa yedek ölçeği kullan
FALLBACK_PIXELS_PER_METER = 40.0         # ÖRNEK Değer

HISTORY_LENGTH = 15               # her araç için saklanacak son kare sayısı
MIN_PIXEL_DISTANCE = 1.0          # bunun altı "duruyor/gürültü" sayılır
MAX_PIXEL_DISTANCE = 250.0        # bunun üstü "tracking hatası/outlier" sayılır

SMOOTHING_WINDOW = 10             # hız ortalaması için son kaç kare kullanılsın
MAX_REALISTIC_SPEED_KMH = 200.0   # bunun üstü ölçüm hatası sayılır, iptal edilir

# --- KARAR EŞİKLERİ (Decision Layer) ---
# Bu üç eşik, projedeki "hangi araç tehlikeli/kurallara aykırı" kararını verir.
SPEED_LIMIT_KMH = 50.0            # bu hızın üstü -> HIZ İHLALİ
LANE_VIOLATION_TOLERANCE_PX = 15  # araç merkezi şerit sınırına bu kadar yakınsa "şerit ihlali" say
MIN_DISPLACEMENT_FOR_DIRECTION_PX = 4.0  # bu kadar küçük hareket varsa yön hesaplama (gürültü olur)

# --- Stale track temizliği ---
STALE_TRACK_TIMEOUT_FRAMES = 30   # bu kadar kare görünmeyen araç hafızadan silinir

# --- Görselleştirme Renkleri (BGR formatında, OpenCV böyle ister) ---
COLOR_NORMAL = (0, 255, 0)        # yeşil  -> her şey normal
COLOR_SPEED_VIOLATION = (0, 0, 255)   # kırmızı -> hız ihlali
COLOR_LANE_VIOLATION = (0, 165, 255)  # turuncu -> şerit ihlali
COLOR_LANE_LINE = (255, 200, 0)
COLOR_TEXT = (255, 255, 255)

# --- Yazı / Etiket Boyutu ---
FONT_SCALE = 0.9          # varsayılan 0.5'ti, büyüttük.
FONT_THICKNESS = 2        # yazı kalınlığı
BOX_THICKNESS = 3         # kutu çizgisinin kalınlığı 

DEBUG = False   