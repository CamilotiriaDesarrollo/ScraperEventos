"""Publica mensajes a canales de WhatsApp Web vía Playwright.

Usa `launch_persistent_context` con un user_data_dir local porque WhatsApp Web
guarda sus claves de sesión en IndexedDB (no en cookies/localStorage), y solo
un perfil persistente las preserva entre corridas.

Uso:
    # 1. Setup inicial — escanear QR (una vez por dispositivo, dura ~14 días):
    python whatsapp_publisher.py --setup

    # 2. Publicar un mensaje al canal TEST (modo de prueba):
    python whatsapp_publisher.py --canal TEST --texto "hola desde el bot"

    # 3. Desde Python:
    from whatsapp_publisher import publicar
    publicar("https://web.whatsapp.com/channel/...", "*Hola* mundo")
"""
import argparse
import logging
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from config import USER_AGENT, WA_CANALES, WA_SESSION_DIR

logger = logging.getLogger(__name__)

USER_DATA_DIR = WA_SESSION_DIR / "user-data"


def _abrir_contexto(playwright, headless):
    """Lanza Chromium con user_data_dir persistente. Preserva IndexedDB de WA Web."""
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=headless,
        user_agent=USER_AGENT,
        locale="es-CO",
        viewport={"width": 1280, "height": 900},
    )
    page = context.pages[0] if context.pages else context.new_page()
    return context, page


def _esperar_app_cargada(page, timeout_ms=45000):
    """Espera a que WhatsApp Web salga de la pantalla de carga inicial."""
    selectores_app = [
        "#pane-side",
        "[aria-label='Lista de chats']",
        "[aria-label='Chat list']",
        "header[data-testid='chatlist-header']",
        "div[role='grid']",
    ]
    elapsed = 0
    step = 1500
    while elapsed < timeout_ms:
        for sel in selectores_app:
            try:
                if page.locator(sel).count() > 0:
                    return True
            except Exception:
                continue
        page.wait_for_timeout(step)
        elapsed += step
    return False


def setup_session(timeout_seg=180):
    """Abre WhatsApp Web no-headless para escanear el QR. Detecta automáticamente
    cuando la sesión inicia (lista de chats visible) y persiste el perfil."""
    from playwright.sync_api import sync_playwright

    print()
    print("=" * 60)
    print("SETUP de sesión WhatsApp Web")
    print("=" * 60)
    print("1. Se abrirá Chromium con WhatsApp Web.")
    print("2. Escaneá el QR con tu teléfono (WhatsApp > Dispositivos vinculados).")
    print(f"3. El script detectará el login automáticamente (timeout {timeout_seg}s).")
    print()

    with sync_playwright() as p:
        context, page = _abrir_contexto(p, headless=False)
        page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded")

        if _esperar_app_cargada(page, timeout_ms=timeout_seg * 1000):
            page.wait_for_timeout(3000)
            print(f"\nSesion logueada y guardada en {USER_DATA_DIR}")
            context.close()
            return True
        else:
            print("Timeout: no detecte login. Escaneaste el QR?")
            context.close()
            return False


def _abrir_canal(page, nombre_canal):
    """Click en sidebar 'Canales' y luego en el item con el nombre indicado."""
    logger.info("Click en sidebar 'Canales'…")
    page.locator('button[aria-label="Canales"]').first.click()
    page.wait_for_timeout(4000)

    # Buscar el item de canal por nombre. WhatsApp lo pone en un span dentro de listitem.
    logger.info(f"Buscando canal '{nombre_canal}'…")
    canal_item = None
    for intento in range(8):
        items = page.locator('[role="listitem"]')
        count = items.count()
        for i in range(count):
            item = items.nth(i)
            try:
                texto = item.inner_text()
                # nombre suele estar en la primera línea
                primera_linea = texto.split("\n")[0].strip() if texto else ""
                if primera_linea.lower() == nombre_canal.lower():
                    canal_item = item
                    break
            except Exception:
                continue
        if canal_item is not None:
            break
        page.wait_for_timeout(1000)

    if canal_item is None:
        return False

    canal_item.click()
    page.wait_for_timeout(3500)
    return True


def _esperar_preview_link(page, max_seg=15):
    """Espera a que aparezca la card del preview de link (con imagen cargada)."""
    preview_selectors = [
        '[data-testid="link-preview"]',
        'div[role="link-preview"]',
        '[data-testid="media-url"]',
        'div[class*="link-preview"]',
        'div[class*="rich-preview"]',
    ]
    elapsed = 0
    step = 700
    encontrado = False
    while elapsed < max_seg * 1000:
        for sel in preview_selectors:
            try:
                if page.locator(sel).count() > 0:
                    encontrado = True
                    break
            except Exception:
                continue
        if encontrado:
            break
        page.wait_for_timeout(step)
        elapsed += step

    if encontrado:
        # Margen extra para que la imagen del preview termine de bajar
        page.wait_for_timeout(2500)
        return True
    return False


def publicar(canal_nombre, texto, headless=True, esperar_preview_seg=15):
    """Envía `texto` al canal con `canal_nombre` (nombre exacto como aparece en WhatsApp Web).
    Retorna True si éxito."""
    if not canal_nombre:
        logger.error("canal_nombre vacío")
        return False
    if not USER_DATA_DIR.exists() or not any(USER_DATA_DIR.iterdir()):
        logger.error(f"No existe perfil persistente en {USER_DATA_DIR}. Corre 'python whatsapp_publisher.py --setup'")
        return False

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context, page = _abrir_contexto(p, headless=headless)
        try:
            logger.info("Cargando WhatsApp Web…")
            page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded")
            if not _esperar_app_cargada(page):
                logger.error("WhatsApp Web no cargó (sigue en pantalla de inicio).")
                page.screenshot(path=str(WA_SESSION_DIR / "error_no_carga.png"))
                return False

            page.wait_for_timeout(2000)

            if not _abrir_canal(page, canal_nombre):
                logger.error(f"No encontré el canal '{canal_nombre}' en la pestaña Canales.")
                page.screenshot(path=str(WA_SESSION_DIR / "error_canal_no_encontrado.png"))
                return False

            input_selectors = [
                'footer div[contenteditable="true"][role="textbox"]',
                'div[contenteditable="true"][data-tab="10"]',
                'div[contenteditable="true"][data-tab="6"]',
                'div[contenteditable="true"][role="textbox"]',
                'div[role="textbox"][contenteditable="true"]',
            ]
            input_box = None
            for intento in range(15):
                for sel in input_selectors:
                    try:
                        loc = page.locator(sel).last
                        if loc.count() > 0:
                            input_box = loc
                            break
                    except Exception:
                        continue
                if input_box is not None:
                    break
                page.wait_for_timeout(1000)

            if input_box is None:
                logger.error("No se encontró el cuadro de texto. Posible: no eres admin del canal.")
                page.screenshot(path=str(WA_SESSION_DIR / "error_no_input.png"))
                return False

            input_box.click()
            page.wait_for_timeout(700)

            for i, linea in enumerate(texto.split("\n")):
                if i > 0:
                    page.keyboard.press("Shift+Enter")
                page.keyboard.type(linea, delay=15)

            # Esperar a que WhatsApp genere el preview del link (con imagen)
            if "http" in texto:
                preview_ok = _esperar_preview_link(page, max_seg=esperar_preview_seg)
                if not preview_ok:
                    logger.warning("No se detectó preview del link tras esperar; envío igual.")
            else:
                page.wait_for_timeout(2000)

            send_selectors = [
                'button[aria-label="Enviar"]',
                'button[aria-label="Send"]',
                'span[data-icon="send"]',
                'button[data-tab="11"]',
            ]
            sent = False
            for sel in send_selectors:
                try:
                    btn = page.locator(sel).last
                    if btn.count() > 0:
                        btn.click()
                        sent = True
                        break
                except Exception:
                    continue
            if not sent:
                page.keyboard.press("Enter")
                sent = True

            page.wait_for_timeout(3500)
            logger.info("Publicación enviada.")
            return True
        except Exception as exc:
            logger.error(f"Error publicando: {exc}")
            try:
                page.screenshot(path=str(WA_SESSION_DIR / "error_publicar.png"))
            except Exception:
                pass
            return False
        finally:
            context.close()


def _cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true", help="Escanea QR y guarda sesión")
    parser.add_argument("--canal", default="TEST", help="Nombre del canal (TEST/Bogotá/Pereira)")
    parser.add_argument("--texto", default="", help="Texto a publicar")
    parser.add_argument("--no-headless", action="store_true", help="Mostrar navegador (debug)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if args.setup:
        setup_session()
        return 0

    if not args.texto:
        print("ERROR: pasa --texto 'mensaje a publicar'", file=sys.stderr)
        return 2

    canal_url = WA_CANALES.get(args.canal, "")
    if not canal_url:
        print(f"ERROR: canal '{args.canal}' no configurado en WA_CANALES (config.py o .env)", file=sys.stderr)
        return 2

    ok = publicar(canal_url, args.texto, headless=not args.no_headless)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_cli())
