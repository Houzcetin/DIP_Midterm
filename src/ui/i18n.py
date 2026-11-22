"""Runtime translation of English UI strings."""

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QObject, QTranslator, Signal


LANGUAGES = {"en": "English", "tr": "Türkçe"}

TURKISH = {
    # Window, menus, and dialogs
    "DIP Midterm – Image Processing Application": "DIP Ara Sınavı – Görüntü İşleme Uygulaması",
    "&File": "&Dosya",
    "&Open...": "&Aç...",
    "&Save Result As...": "Sonucu &Farklı Kaydet...",
    "E&xit": "Çı&kış",
    "Recent Files": "Son Dosyalar",
    "Sample Images": "Örnek Görüntüler",
    "&Edit": "Dü&zenle",
    "&Undo": "&Geri Al",
    "&Redo": "&Yinele",
    "Reset to &Original": "Özgün Görüntüye &Dön",
    "&Use Result as Original": "Sonucu Ö&zgün Görüntü Olarak Kullan",
    "Auto Enhance...": "Otomatik İyileştirme...",
    "Auto Enhance": "Otomatik İyileştirme",
    "Analyze the image and fix noise, color, contrast, exposure and sharpness (Ctrl+E).":
        "Görüntüyü analiz eder; gürültü, renk, kontrast, pozlama ve keskinliği düzeltir (Ctrl+E).",
    "Auto Enhance could not process this image.": "Otomatik İyileştirme bu görüntüyü işleyemedi.",
    "&View": "&Görünüm",
    "Fit to Window": "Pencereye Sığdır",
    "Actual Size 100%": "Gerçek Boyut %100",
    "Zoom In": "Yakınlaştır",
    "Zoom Out": "Uzaklaştır",
    "Show Original in Result panel": "Özgün Görüntüyü Sonuç Panelinde Göster",
    "Before/After Slider": "Önce/Sonra Sürgüsü",
    "Show Histogram Window…": "Histogram Penceresini Göster…",
    "Frequency Inspector…": "Frekans İnceleyici…",
    "Theme": "Tema",
    "Language": "Dil",
    "&Help": "&Yardım",
    "Keyboard Shortcuts": "Klavye Kısayolları",
    "About": "Hakkında",
    "Mouse wheel  —  Zoom around the pointer": "Fare tekerleği  —  İşaretçinin çevresinde yakınlaştır veya uzaklaştır",
    "Left drag  —  Pan a zoomed image": "Sol tuşla sürükle  —  Yakınlaştırılmış görüntüyü kaydır",
    "Drag the Before/After divider  —  Move the wipe": "Önce/Sonra ayırıcısını sürükle  —  Karşılaştırma sınırını kaydır",
    "Double-click  —  Fit to Window": "Çift tıkla  —  Pencereye sığdır",
    "About DIP Midterm": "DIP Ara Sınavı Hakkında",
    "COMP 4360 Midterm\nDigital Image Processing\n\nBuilt with PySide6 and OpenCV.":
        "COMP 4360 Ara Sınavı\nSayısal Görüntü İşleme\n\nPySide6 ve OpenCV ile geliştirildi.",
    "Open Image": "Görüntü Aç",
    "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)": "Görüntüler (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
    "Save Result": "Sonucu Kaydet",
    "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)": "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)",
    "&Look in:": "&Konum:",
    "Files of &type:": "Dosya &türü:",
    "&Step down": "Bir adım a&zalt",
    "Error": "Hata",
    "Could not open image: {path}": "Görüntü açılamadı: {path}",
    "Could not save image: {path}": "Görüntü kaydedilemedi: {path}",
    "File not found: {path}": "Dosya bulunamadı: {path}",
    "Permission denied: {path}": "Erişim izni yok: {path}",
    "No image": "Görüntü yok",
    "Please open an image first.": "Lütfen önce bir görüntü açın.",
    "Operation failed": "İşlem başarısız",
    "Could not apply {operation}.": "{operation} işlemi uygulanamadı.",
    "Preview failed: {operation}": "Önizleme oluşturulamadı: {operation}",

    # Auto Enhance report
    "Auto Enhance Report": "Otomatik İyileştirme Raporu",
    "Close": "Kapat",
    "Detected": "Tespit edilenler",
    "Applied steps": "Uygulanan adımlar",
    "Before → After": "Önce → Sonra",
    "Well-exposed image": "Pozlaması dengeli görüntü",
    "Dark image": "Karanlık görüntü",
    "Bright image": "Parlak görüntü",
    "Grayscale image": "Gri tonlamalı görüntü",
    "Color image": "Renkli görüntü",
    "Mean brightness": "Ortalama parlaklık",
    "Overall contrast": "Genel kontrast",
    "Luminance range (2nd–98th percentile)": "Parlaklık aralığı (2. ve 98. yüzdelikler)",
    "Local contrast": "Yerel kontrast",
    "Isolated black and white pixels": "Çevresinden ayrışan siyah ve beyaz pikseller",
    "Estimated Gaussian noise (8-bit sigma)": "Tahmini Gauss gürültüsü (8 bit sigma)",
    "Sharpness (Laplacian variance)": "Keskinlik (Laplasyen varyansı)",
    "Color cast (channel mean deviation)": "Renk sapması (kanal ortalamalarının sapması)",
    "Mean saturation": "Ortalama doygunluk",
    "Reduce isolated black and white pixels ({fraction:.1%}).":
        "Çevresinden ayrışan siyah ve beyaz pikselleri ({fraction:.1%}) azaltmak için.",
    "Reduce estimated Gaussian noise (sigma {sigma:.1f}) while preserving edges.":
        "Kenarları koruyarak tahmini Gauss gürültüsünü (sigma {sigma:.1f}) azaltmak için.",
    "Reduce the imbalance between channel means ({cast:.2f}).":
        "Kanal ortalamaları arasındaki dengesizliği ({cast:.2f}) azaltmak için.",
    "Expand the narrow luminance range ({spread:.2f}).":
        "Dar parlaklık aralığını ({spread:.2f}) genişletmek için.",
    "Increase weak local contrast ({contrast:.3f}).":
        "Düşük yerel kontrastı ({contrast:.3f}) artırmak için.",
    "Move mean brightness ({mean:.2f}) toward {target:.2f}.":
        "Ortalama parlaklığı ({mean:.2f}) {target:.2f} hedefine yaklaştırmak için.",
    "Bring out soft edges (sharpness {sharpness:.5f}).":
        "Bulanık kenarları belirginleştirmek için (keskinlik {sharpness:.5f}).",
    "The image already looks well exposed, clean and sharp.":
        "Görüntü zaten dengeli pozlanmış, temiz ve keskin görünüyor.",

    # Image panels, status, plots, and themes
    "Operations": "İşlemler",
    "Histogram": "Histogram",
    "History": "Geçmiş",
    "Original": "Özgün Görüntü",
    "Result": "Sonuç",
    "Result — showing Original": "Sonuç — Özgün Görüntü gösteriliyor",
    "Drag to resize the panels; double-click to split evenly.":
        "Panel boyutlarını değiştirmek için sürükleyin, eşitlemek için çift tıklayın.",
    "Before": "Önce",
    "After": "Sonra",
    "Preview — press Apply to keep": "Önizleme — korumak için Uygula'ya basın",
    "sizes differ — original stretched": "boyutlar farklı — özgün görüntü sonuca uyarlandı",
    "{coordinates} | Gray={value}": "{coordinates} | Gri={value}",
    "{coordinates} | R,G,B={r},{g},{b}": "{coordinates} | R,G,B={r},{g},{b}",
    "Saved: {path}": "Kaydedildi: {path}",
    "Open an image to start (Ctrl+O)": "Başlamak için bir görüntü açın (Ctrl+O)",
    "{name}  |  {width}×{height}  |  {channels} channel(s)  |  step {index}/{last}":
        "{name}  |  {width}×{height}  |  {channels} kanal  |  adım {index}/{last}",
    "Intensity": "Yoğunluk",
    "Pixel count": "Piksel sayısı",
    "Frequency Inspector": "Frekans İnceleyici",
    "Magnitude spectrum": "Genlik spektrumu",
    "Filter mask": "Filtre maskesi",
    "Filtered preview": "Filtrelenmiş önizleme",
    "Center = low frequencies · Edges = high frequencies":
        "Merkez = düşük frekanslar · Kenarlar = yüksek frekanslar",
    "Open an image to start": "Başlamak için bir görüntü açın",
    "Red": "Kırmızı",
    "Yellow": "Sarı",
    "Blue": "Mavi",
    "Pink": "Pembe",
    "Green": "Yeşil",
    "Purple": "Mor",
    "{color} theme": "{color} tema",

    # Samples
    "Colorful shapes": "Renkli şekiller",
    "Try Grayscale, Negative, or Histogram equalization.":
        "Gri tonlama, Negatif veya Histogram eşitleme işlemlerini deneyin.",
    "Noisy (salt & pepper)": "Gürültülü (tuz ve biber)",
    "Compare Median with Box or Gaussian blur.":
        "Medyan filtreyi kutu veya Gauss bulanıklığıyla karşılaştırın.",
    "Low-contrast landscape": "Düşük kontrastlı manzara",
    "Try Contrast stretch, Gamma, Histogram equalization, or CLAHE.":
        "Kontrast germe, Gama, Histogram eşitleme veya CLAHE işlemlerini deneyin.",
    "Unevenly lit document": "Düzensiz aydınlatılmış belge",
    "Compare Global and Otsu thresholds, then try morphology.":
        "Genel eşikleme ile Otsu eşiklemesini karşılaştırın, ardından morfolojik işlemleri deneyin.",
    "Binary shapes with holes": "Delikli ikili şekiller",
    "Try Opening, Closing, Erode, and Dilate.": "Açma, Kapama, Aşındırma ve Genişletme işlemlerini deneyin.",
    "Checkerboard grid": "Dama tahtası ızgarası",
    "Try Rotate, Scale, Shear, or Translate.": "Döndürme, Ölçekleme, Eğme veya Öteleme işlemlerini deneyin.",
    "Edges and zone plate": "Kenarlar ve bölge plakası",
    "Try Sobel, Laplacian, Canny, or FFT spectrum.": "Sobel, Laplacian, Canny veya FFT spektrumunu deneyin.",
    "Periodic stripe noise": "Periyodik çizgi gürültüsü",
    "Try FFT spectrum, then Ideal Band-stop with cutoff 31 and width 4.":
        "FFT spektrumunu, ardından kesim yarıçapı 31 ve bant genişliği 4 olan ideal bant durduran filtreyi deneyin.",

    # Operations toolbox
    "A Basics": "A Temel İşlemler",
    "B Affine": "B Afin Dönüşümler",
    "C Intensity": "C Yoğunluk",
    "D Spatial Filters": "D Uzamsal Filtreler",
    "E Histogram": "E Histogram",
    "F Morphology": "F Morfoloji",
    "Extras": "Ek İşlemler",
    "G Frequency": "G Frekans",
    "Quick actions": "Hızlı işlemler",
    "Apply": "Uygula",
    "Reset": "Sıfırla",
    "Return to the original image (undoable, Ctrl+R).": "Özgün görüntüye dön (geri alınabilir, Ctrl+R).",
    "Flip H": "Yatay çevir",
    "Flip V": "Dikey çevir",
    "Rotate 90° CW": "90° sağa döndür",
    "Rotate 90° CCW": "90° sola döndür",
    "Grayscale": "Gri tonlama",
    "Flip": "Çevirme",
    "Rotate 90 degrees": "90 derece döndürme",
    "Rotate": "Döndürme",
    "Scale": "Ölçekleme",
    "Translate": "Öteleme",
    "Shear": "Eğme",
    "Contrast stretch": "Kontrast germe",
    "Gamma correction": "Gama düzeltme",
    "Negative": "Negatif",
    "Box blur": "Kutu bulanıklığı",
    "Gaussian blur": "Gauss bulanıklığı",
    "Median filter": "Medyan filtre",
    "Laplacian edges": "Laplacian kenar algılama",
    "Sobel edges": "Sobel kenar algılama",
    "Histogram equalization": "Histogram eşitleme",
    "Threshold": "Eşikleme",
    "Erode": "Aşındırma",
    "Dilate": "Genişletme",
    "Opening": "Açma",
    "Closing": "Kapama",
    "CLAHE": "CLAHE",
    "Unsharp mask": "Keskinleştirme maskesi",
    "Canny edges": "Canny kenar algılama",
    "Add noise": "Gürültü ekleme",
    "Sepia": "Sepya",
    "Bilateral filter": "Çift taraflı filtre",
    "White balance": "Beyaz dengesi",
    "Strength": "Düzeltme düzeyi",
    "Blend gray-world color correction from 0 (off) to 1 (full).":
        "Gri dünya renk düzeltmesini 0 (kapalı) ile 1 (tam) arasında uygular.",
    "FFT spectrum": "FFT spektrumu",
    "Frequency filter": "Frekans filtresi",

    # Parameters and choices
    "Kernel size": "Çekirdek boyutu",
    "Kernel shape": "Çekirdek şekli",
    "Iterations": "Yineleme sayısı",
    "Expand canvas": "Tuvali genişlet",
    "Direction": "Yön",
    "Quarter-turns clockwise": "Saat yönünde çeyrek tur sayısı",
    "Angle (degrees)": "Açı (derece)",
    "Border intensity": "Kenar dolgu yoğunluğu",
    "Horizontal factor": "Yatay ölçek katsayısı",
    "Vertical factor": "Dikey ölçek katsayısı",
    "Interpolation": "Enterpolasyon",
    "Horizontal shift (pixels)": "Yatay öteleme (piksel)",
    "Vertical shift (pixels)": "Dikey öteleme (piksel)",
    "Horizontal shear": "Yatay eğme",
    "Vertical shear": "Dikey eğme",
    "Lower percentile": "Alt yüzdelik",
    "Upper percentile": "Üst yüzdelik",
    "Gamma": "Gama",
    "Sigma": "Sigma",
    "Method": "Yöntem",
    "Invert": "Tersine çevir",
    "Clip limit": "Kırpma sınırı",
    "Tiles per axis": "Eksen başına blok sayısı",
    "Blur kernel size": "Bulanıklaştırma çekirdeğinin boyutu",
    "Sharpening amount": "Keskinleştirme miktarı",
    "Lower threshold": "Alt eşik",
    "Upper threshold": "Üst eşik",
    "Noise type": "Gürültü türü",
    "Amount": "Miktar",
    "Random seed": "Rastgelelik tohumu",
    "Diameter": "Çap",
    "Color sigma": "Renk sigması",
    "Spatial sigma": "Uzamsal sigma",
    "Log magnitude": "Logaritmik genlik",
    "Filter type": "Filtre türü",
    "Mask shape": "Maske şekli",
    "Cutoff radius (px)": "Kesim yarıçapı (piksel)",
    "Band width (px)": "Bant genişliği (piksel)",
    "Butterworth order": "Butterworth derecesi",
    "Horizontal": "Yatay",
    "Vertical": "Dikey",
    "Both": "Her ikisi",
    "X": "X",
    "Y": "Y",
    "Nearest": "En yakın komşu",
    "Linear": "Doğrusal",
    "Cubic": "Kübik",
    "Area": "Alan",
    "Lanczos": "Lanczos",
    "Global (t)": "Genel (t)",
    "Otsu (auto)": "Otsu (otomatik)",
    "Rect": "Dikdörtgen",
    "Ellipse": "Elips",
    "Cross": "Artı",
    "Salt & pepper": "Tuz ve biber",
    "Low-pass": "Alçak geçiren",
    "High-pass": "Yüksek geçiren",
    "Band-pass": "Bant geçiren",
    "Band-stop": "Bant durduran",
    "Ideal": "İdeal",
    "Gaussian": "Gauss",
    "Butterworth": "Butterworth",
    "Yes": "Evet",
    "No": "Hayır",

    # Registry tooltips
    "Odd neighborhood width; even sizes round up.": "Komşuluk genişliği tek sayıdır. Çift değerler yukarı yuvarlanır.",
    "Structuring element shape.": "Yapılandırma elemanının şekli.",
    "Number of erosions/dilations in each stage.": "Her aşamadaki aşındırma veya genişletme sayısı.",
    "Fit the full transformed image without cropping.": "Dönüştürülen görüntünün tamamını kırpmadan sığdırır.",
    "Horizontal, vertical, or both axes.": "Yatay eksen, dikey eksen veya her iki eksen.",
    "Modulo 4: 1 is clockwise; -1 or 3 is counterclockwise.":
        "Mod 4: 1 saat yönünde, -1 veya 3 saat yönünün tersine döndürür.",
    "Positive angles turn counterclockwise about the center.": "Pozitif açılar merkez etrafında saat yönünün tersine döndürür.",
    "Fill intensity outside the image; 0 is black.": "Görüntü dışındaki dolgu yoğunluğu. 0 siyahı belirtir.",
    "Width multiplier; result is at least one pixel.": "Genişlik çarpanı. Sonuç en az bir pikseldir.",
    "Height multiplier; result is at least one pixel.": "Yükseklik çarpanı. Sonuç en az bir pikseldir.",
    "How resized pixel values are sampled.": "Boyutlandırma sırasında piksel değerlerinin nasıl örnekleneceği.",
    "Positive shifts right; canvas size stays fixed.": "Pozitif değerler sağa öteler. Tuval boyutu sabit kalır.",
    "Positive shifts down; exposed pixels are black.": "Pozitif değerler aşağı öteler. Açığa çıkan pikseller siyahtır.",
    "Adds shx times y to x; use 0 for no horizontal shear.": "x koordinatına shx × y ekler. 0 yatay eğmeyi devre dışı bırakır.",
    "Adds shy times x to y; use 0 for no vertical shear.": "y koordinatına shy × x ekler. 0 dikey eğmeyi devre dışı bırakır.",
    "Per-channel percentile mapped to black.": "Her kanalda siyaha eşlenen yüzdelik.",
    "Per-channel percentile mapped to white.": "Her kanalda beyaza eşlenen yüzdelik.",
    "Exponent: above 1 darkens; below 1 brightens; 1 is unchanged.":
        "Üs 1'den büyükse görüntüyü koyulaştırır, 1'den küçükse aydınlatır. 1 görüntüyü değiştirmez.",
    "Gaussian standard deviation; 0 derives it from kernel size.":
        "Gauss standart sapması. 0 girilirse çekirdek boyutundan hesaplanır.",
    "Odd neighborhood width, at least 3.": "En az 3 olan tek sayılı komşuluk genişliği.",
    "Absolute x/y derivative or Euclidean magnitude; output is gray.":
        "x veya y türevinin mutlak değeri ya da Öklid normu. Çıktı gri tonlamalıdır.",
    "Global uses t; Otsu estimates the threshold automatically.":
        "Genel eşikleme t değerini kullanır. Otsu eşiği otomatik olarak hesaplar.",
    "Global cutoff; output is binary gray.": "Genel eşik değeri. Çıktı ikili gri tonlamalıdır.",
    "Swap black and white in the binary result.": "İkili sonuçta siyah ile beyazın yerini değiştirir.",
    "Contrast limit; color equalizes LAB lightness only.": "Kontrast sınırı. Renkli görüntülerde yalnızca LAB açıklığı eşitlenir.",
    "Number of grid tiles per axis, not tile width in pixels.": "Izgaranın her eksenindeki blok sayısı.",
    "Odd Gaussian width used to extract detail.": "Ayrıntıları çıkarmak için kullanılan tek sayılı Gauss çekirdek genişliği.",
    "Multiplier of the detail residual; 0 is unchanged.": "Ayrıntı bileşeninin çarpanı. 0 görüntüyü değiştirmez.",
    "Weak-edge threshold; the pair is sorted automatically.": "Zayıf kenar eşiği. İki eşik otomatik olarak sıralanır.",
    "Strong-edge threshold; output is gray.": "Güçlü kenar eşiği. Çıktı gri tonlamalıdır.",
    "Impulse noise or additive normal noise.": "Darbe gürültüsü veya toplamsal normal gürültü.",
    "Salt/pepper pixel fraction, or Gaussian standard deviation divided by 255.":
        "Tuz ve biber gürültüsünden etkilenen piksel oranı veya Gauss standart sapmasının 255'e bölümü.",
    "Same seed gives repeatable noise; the Python API also accepts None.":
        "Aynı tohum aynı gürültüyü üretir. Python API'si None değerini de kabul eder.",
    "Odd neighborhood diameter.": "Tek sayılı komşuluk çapı.",
    "Larger values mix more dissimilar intensities.": "Daha büyük değerler, yoğunlukları daha farklı olan pikselleri karıştırır.",
    "Larger values mix pixels over larger distances.": "Daha büyük değerler, birbirinden daha uzak pikselleri karıştırır.",
    "Compress the magnitude range to reveal weaker frequencies.": "Daha zayıf frekansları görünür kılmak için genlik aralığını sıkıştırır.",
    "Pass or suppress low, high, or a band of frequencies.": "Alçak, yüksek veya belirli bir banttaki frekansları geçirir ya da bastırır.",
    "Choose a sharp or gradual transition between frequencies.": "Frekanslar arasında keskin veya kademeli bir geçiş seçin.",
    "Radius from the spectrum center. Sets the ring center for band filters.":
        "Spektrum merkezinden ölçülen yarıçap. Bant filtrelerinde halkanın orta çizgisini belirler.",
    "Full width of the ring for band-pass and band-stop.": "Bant geçiren ve bant durduran filtrelerde halkanın toplam genişliği.",
    "Higher orders give a sharper Butterworth transition.": "Daha yüksek dereceler daha keskin bir Butterworth geçişi sağlar.",
}

missing_keys: set[str] = set()


class _LanguageNotifications(QObject):
    changed = Signal()


class _QtTranslator(QTranslator):
    """Fill gaps in Qt's Turkish catalog for controls used by the app."""

    _SUPPLEMENT = {
        "QFileDialog": {"&Look in:", "Files of &type:"},
        "QAbstractSpinBox": {"&Step down"},
    }

    def translate(self, context, sourceText, disambiguation=None, n=-1):
        if sourceText in self._SUPPLEMENT.get(context, ()):
            return tr(sourceText)
        return super().translate(context, sourceText, disambiguation, n) or None


language_changed = _LanguageNotifications()
_language = "en"
_qt_translator = None


def current_language() -> str:
    return _language


def set_language(language: str | None) -> None:
    """Switch the application language and notify open windows."""
    global _language, _qt_translator
    language = language if isinstance(language, str) and language in LANGUAGES else "en"
    changed = language != _language
    _language = language
    app = QCoreApplication.instance()
    if app is not None:
        if language == "en" and _qt_translator is not None:
            app.removeTranslator(_qt_translator)
            _qt_translator = None
        elif language == "tr" and _qt_translator is None:
            translator = _QtTranslator()
            directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
            if translator.load("qtbase_tr", directory):
                app.installTranslator(translator)
                _qt_translator = translator
    if changed:
        language_changed.changed.emit()


def tr(text: str) -> str:
    """Translate an English source string and record catalog misses in Turkish."""
    if _language == "en" or not text:
        return text
    if text not in TURKISH:
        missing_keys.add(text)
    return TURKISH.get(text, text)
