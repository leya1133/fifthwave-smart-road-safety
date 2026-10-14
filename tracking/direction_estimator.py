
# Aracın hareket geçmişine bakarak hangi yöne gittiğini bulur.
#
# NOT: Sadece ilk ve son noktaya bakmak yerine, ARDIŞIK TÜM noktalar
# arasındaki hareketleri topluyoruz. Böylece bir araç yön değiştirirse
# (örn. şerit değiştirirken sağa sonra sola kırarsa) bu hareket kaybolmaz,
# sistem bunu fark edebilir. Bu, "yönleri değişen araçları tespit etmek"
# istediğin senaryo için önemlidir.

import math
import config


def calculate_direction_angle(history):
    """
    Geçmişteki TÜM ardışık hareket vektörlerini toplayıp genel yönü hesaplar.
    Ekranda x sağa, y aşağı pozitiftir; açıyı normal matematik yönüne çeviriyoruz
    (0°=sağ, 90°=yukarı, 180°=sol, 270°=aşağı).

    Döndürür: derece [0,360) veya yetersiz hareket varsa None
    """
    if len(history) < 2:
        return None

    dx_total = 0.0
    dy_total = 0.0
    for i in range(1, len(history)):
        x1, y1, _ = history[i - 1]
        x2, y2, _ = history[i]
        dx_total += (x2 - x1)
        dy_total += (y2 - y1)

    displacement = math.sqrt(dx_total ** 2 + dy_total ** 2)
    if displacement < config.MIN_DISPLACEMENT_FOR_DIRECTION_PX:
        return None  # araç yeterince hareket etmedi, güvenilir yön yok

    angle = math.degrees(math.atan2(-dy_total, dx_total))
    return angle % 360


def get_direction_label(angle):
    """
    Açıyı Kuzey/Güney/Doğu/Batı etiketine çevirir.

    ÖNEMLİ NOT: Kamerada GPS/pusula yok, bu yüzden bu yönler GERÇEK coğrafi
    yön değildir. Burada "ekranın üst kenarı = KUZEY" kabul ediyoruz (yani
    kamera kuzeye bakıyor gibi davranıyoruz). Eğer kameranız gerçekte başka
    bir yöne bakıyorsa, bu etiketler ona göre KAYDIRILMALIDIR .
    

    8 yönlü pusula etiketi döner: KUZEY, GUNEY, DOGU, BATI,
    KUZEYDOGU, KUZEYBATI, GUNEYDOGU, GUNEYBATI
    """
    if angle is None:
        return "BILINMIYOR"

    # 8 yönlü pusula: her dilim 45 derece, sınırlar 22.5 derece kaydırılmış
    if 67.5 <= angle < 112.5:
        return "KUZEY"
    if 112.5 <= angle < 157.5:
        return "KUZEYBATI"
    if 157.5 <= angle < 202.5:
        return "BATI"
    if 202.5 <= angle < 247.5:
        return "GUNEYBATI"
    if 247.5 <= angle < 292.5:
        return "GUNEY"
    if 292.5 <= angle < 337.5:
        return "GUNEYDOGU"
    if angle >= 337.5 or angle < 22.5:
        return "DOGU"
    return "KUZEYDOGU"  # 22.5 <= angle < 67.5


def detect_direction_change(previous_angle, current_angle, threshold_degrees=45):
    """
    KARAR: Aracın yönü ani bir şekilde değişti mi?
    Bu, ters şeride girme veya tehlikeli manevra gibi durumları yakalamak
    için kullanılabilir. İki açı arasındaki en kısa farkı hesaplar
    (örn. 350° ile 10° arasındaki fark 20°'dir, 340° değil).

    previous_angle / current_angle: None olabilir, bu durumda False döner.
    """
    if previous_angle is None or current_angle is None:
        return False

    diff = abs(current_angle - previous_angle)
    diff = min(diff, 360 - diff)  # dairesel farkı alınır

    return diff > threshold_degrees