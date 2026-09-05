/* global qrcode */
(() => {
  'use strict';

  // Launch checklist: replace null with verified public store URLs.
  // null deliberately uses the local coming-soon screen (no fake install).
  const stores = { ios: null, android: null };
  const androidPackage = 'com.shesafe.shesafe_mobile';
  const params = new URLSearchParams(window.location.search);
  const rawCode = (params.get('code') || '').trim().toUpperCase();
  const code = /^[A-Z0-9]{6,64}$/.test(rawCode) ? rawCode : null;
  const inviteUrl = code ? `https://boonts.com/join?code=${encodeURIComponent(code)}` : null;
  const customLink = code ? `shesafe://join?code=${encodeURIComponent(code)}` : null;
  const ua = navigator.userAgent || '';
  const isAndroid = /Android/i.test(ua);
  const isIOS = /iPhone|iPad|iPod/i.test(ua) || (/Macintosh/i.test(ua) && navigator.maxTouchPoints > 1);
  const isMobile = isAndroid || isIOS;
  const byId = (id) => document.getElementById(id);
  const translations = {
    en: {
      pageTitle: 'SheSafe invitation', eyebrow: 'A little closer. A little safer.',
      desktopTitle: 'Open this invitation on your phone',
      desktopIntro: 'Scan the QR code with your phone’s camera. Open the link on a mobile device with SheSafe installed.',
      mobileTitle: 'You’ve been invited to SheSafe',
      mobileIntro: 'Open the app to review and confirm your invitation.',
      invalidTitle: 'Check your invitation link',
      invalidIntro: 'Ask the person who invited you to send the full link with the invitation code.',
      scan: 'Use your phone’s camera to scan', qrLabel: 'QR code for this SheSafe invitation',
      codeLabel: 'Invitation code', open: 'Open in SheSafe', copy: 'Copy invitation link',
      copied: 'Invitation link copied', copyFailed: 'Copy the invitation link from your browser’s address bar.',
      openHelp: 'If the app does not open, try this link in Safari or Chrome.',
      installTitle: 'Don’t have SheSafe yet?',
      installHelp: 'Once the app is available, install it on your phone and open this invitation again. Your code will be filled in for confirmation.',
      iosStore: 'App Store · coming soon', androidStore: 'Google Play · coming soon',
      storeTitle: 'SheSafe is coming soon',
      storeIntro: 'SheSafe is not available in {store} yet. Come back to this invitation after installing the app.',
      back: 'Back to invitation',
      footer: 'Your circle of care, always close.',
    },
    ru: {
      pageTitle: 'Приглашение в SheSafe', eyebrow: 'Ближе друг к другу. Спокойнее за своих.',
      desktopTitle: 'Откройте приглашение на телефоне',
      desktopIntro: 'Отсканируйте QR-код камерой телефона. Ссылку нужно открыть на мобильном устройстве с установленным приложением SheSafe.',
      mobileTitle: 'Вас пригласили в SheSafe',
      mobileIntro: 'Откройте приложение, чтобы посмотреть и подтвердить приглашение.',
      invalidTitle: 'Проверьте ссылку приглашения',
      invalidIntro: 'Попросите отправить полную ссылку с кодом приглашения.',
      scan: 'Наведите камеру телефона на QR-код', qrLabel: 'QR-код приглашения в SheSafe',
      codeLabel: 'Код приглашения', open: 'Открыть в SheSafe', copy: 'Скопировать ссылку',
      copied: 'Ссылка приглашения скопирована', copyFailed: 'Скопируйте ссылку приглашения из адресной строки браузера.',
      openHelp: 'Если приложение не открывается, попробуйте открыть эту ссылку в Safari или Chrome.',
      installTitle: 'Ещё нет SheSafe?',
      installHelp: 'Когда приложение появится в магазине, установите его на телефон и снова откройте это приглашение. Код подставится на экране подтверждения.',
      iosStore: 'App Store · скоро', androidStore: 'Google Play · скоро',
      storeTitle: 'SheSafe скоро появится в магазине',
      storeIntro: 'SheSafe пока недоступен в {store}. После установки приложения вернитесь к этому приглашению.',
      back: 'Вернуться к приглашению',
      footer: 'Те, кто заботится о вас, всегда рядом.',
    },
  };
  let language = params.get('lang') === 'ru' || (!params.has('lang') && /^ru/i.test(navigator.language)) ? 'ru' : 'en';
  const mockPlatform = params.get('store');
  const isStoreMock = mockPlatform === 'ios' || mockPlatform === 'android';
  const storeUrl = (platform) => stores[platform] || `${window.location.origin}/join/?code=${encodeURIComponent(code)}&store=${platform}&lang=${language}`;

  function translate() {
    const t = translations[language];
    document.documentElement.lang = language;
    document.title = t.pageTitle;
    byId('language').value = language;
    document.querySelectorAll('[data-text]').forEach((element) => {
      element.textContent = t[element.dataset.text];
    });
    byId('title').textContent = t[!code ? 'invalidTitle' : isStoreMock ? 'storeTitle' : isMobile ? 'mobileTitle' : 'desktopTitle'];
    byId('intro').textContent = !code ? t.invalidIntro : isStoreMock
      ? t.storeIntro.replace('{store}', mockPlatform === 'ios' ? 'App Store' : 'Google Play')
      : t[isMobile ? 'mobileIntro' : 'desktopIntro'];
    byId('qr').setAttribute('aria-label', t.qrLabel);
    byId('copy-status').textContent = '';
    if (!code) return;
    byId('ios-store').href = storeUrl('ios');
    byId('android-store').href = storeUrl('android');
    if (stores.ios) byId('ios-store').textContent = 'App Store';
    if (stores.android) byId('android-store').textContent = 'Google Play';
    byId('open').href = isStoreMock ? `/join/?code=${encodeURIComponent(code)}&lang=${language}` : isAndroid
      ? `intent://join?code=${encodeURIComponent(code)}#Intent;scheme=shesafe;package=${androidPackage};S.browser_fallback_url=${encodeURIComponent(storeUrl('android'))};end`
      : customLink;
    if (isStoreMock) byId('open').textContent = t.back;
  }
  byId('language').addEventListener('change', (event) => {
    language = event.target.value;
    translate();
  });
  translate();
  if (!code) {
    byId('install').hidden = true;
    return;
  }

  byId('invite').hidden = false;
  byId('code').textContent = code;
  byId('desktop').hidden = isMobile || isStoreMock;
  byId('open').hidden = !isMobile && !isStoreMock;
  byId('open-help').hidden = !isMobile || isStoreMock;
  byId('install').hidden = isStoreMock;
  byId('ios-store').hidden = isAndroid;
  byId('android-store').hidden = isIOS;

  if (!isMobile && !isStoreMock) {
    try {
      // Generate locally: invitation codes never go to a third-party QR API.
      const qr = qrcode(0, 'M');
      qr.addData(inviteUrl);
      qr.make();
      byId('qr').innerHTML = qr.createSvgTag({ cellSize: 4, margin: 16, scalable: true });
    } catch {
      byId('desktop').hidden = true;
      byId('copy-status').textContent = translations[language].copyFailed;
    }
  }
  byId('copy').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      byId('copy-status').textContent = translations[language].copied;
    } catch {
      byId('copy-status').textContent = translations[language].copyFailed;
    }
  });

  let fallbackTimer;
  const cancelFallback = () => window.clearTimeout(fallbackTimer);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) cancelFallback();
  });
  window.addEventListener('pagehide', cancelFallback);
  window.addEventListener('blur', cancelFallback);
  byId('open').addEventListener('click', () => {
    cancelFallback();
    // Universal Links handle installed apps before this page loads. A browser
    // retry must be user-initiated; cancel fallback when the app takes focus.
    if (isIOS && !isStoreMock) {
      fallbackTimer = window.setTimeout(() => {
        if (!document.hidden) window.location.assign(storeUrl('ios'));
      }, 2000);
    }
  });
})();
