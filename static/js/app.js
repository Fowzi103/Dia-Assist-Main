/* DIA ASSIST — front-end interactions */
(function () {
  'use strict';

  function applyTranslations() {
    const current = window.__I18N__ || {};
    const english = window.__I18N_EN__ || {};
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const value = current[el.getAttribute('data-i18n')];
      if (value) el.textContent = value;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const value = current[el.getAttribute('data-i18n-placeholder')];
      if (value) el.setAttribute('placeholder', value);
    });
    if (window.__LANGUAGE__ === 'en') return;
    const replacements = new Map(Object.keys(english).map(key => [english[key], current[key]]));
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      const trimmed = node.nodeValue.trim();
      if (!trimmed || !replacements.has(trimmed) || !replacements.get(trimmed)) return;
      node.nodeValue = node.nodeValue.replace(trimmed, replacements.get(trimmed));
    });
  }
  applyTranslations();

  /* ---------- Dark mode ---------- */
  const root = document.documentElement;
  const darkToggle = document.getElementById('darkToggle');
  const darkIcon = darkToggle ? darkToggle.querySelector('i') : null;

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    if (darkIcon) darkIcon.className = theme === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    try { localStorage.setItem('dia-theme', theme); } catch (e) {}
  }
  (function initTheme() {
    let saved = 'light';
    try { saved = localStorage.getItem('dia-theme') || 'light'; } catch (e) {}
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(saved === 'auto' ? (prefersDark ? 'dark' : 'light') : saved);
  })();
  if (darkToggle) darkToggle.addEventListener('click', () => {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    toast(next === 'dark' ? 'Dark mode enabled' : 'Light mode enabled', 'info');
  });

  function applyAccessibilityModes() {
    let simple = false;
    let senior = false;
    try { simple = localStorage.getItem('dia-simple-mode') === 'on'; senior = localStorage.getItem('dia-senior-mode') === 'on'; } catch (e) {}
    document.body.classList.toggle('simple-mode', simple);
    document.body.classList.toggle('senior-mode', senior);
  }
  applyAccessibilityModes();
  const simpleModeToggle = document.getElementById('simpleModeToggle');
  const seniorModeToggle = document.getElementById('seniorModeToggle');
  if (simpleModeToggle) simpleModeToggle.addEventListener('click', () => { try { localStorage.setItem('dia-simple-mode', document.body.classList.contains('simple-mode') ? 'off' : 'on'); } catch (e) {} applyAccessibilityModes(); });
  if (seniorModeToggle) seniorModeToggle.addEventListener('click', () => { try { localStorage.setItem('dia-senior-mode', document.body.classList.contains('senior-mode') ? 'off' : 'on'); } catch (e) {} applyAccessibilityModes(); });
  const communicationStyle = document.getElementById('communicationStyle');
  const voicePreference = document.getElementById('voicePreference');
  const darkPreference = document.getElementById('darkPreference');
  try {
    if (communicationStyle) communicationStyle.value = localStorage.getItem('dia-style') || 'professional';
    if (voicePreference) voicePreference.checked = localStorage.getItem('dia-voice') === 'on';
    if (darkPreference) darkPreference.checked = root.getAttribute('data-theme') === 'dark';
  } catch (e) {}
  if (communicationStyle) communicationStyle.addEventListener('change', () => { try { localStorage.setItem('dia-style', communicationStyle.value); } catch (e) {} if (communicationStyle.value === 'simple') { try { localStorage.setItem('dia-simple-mode', 'on'); } catch (e) {} applyAccessibilityModes(); } if (communicationStyle.value === 'senior') { try { localStorage.setItem('dia-senior-mode', 'on'); } catch (e) {} applyAccessibilityModes(); } });
  if (voicePreference) voicePreference.addEventListener('change', () => { try { localStorage.setItem('dia-voice', voicePreference.checked ? 'on' : 'off'); } catch (e) {} });
  if (darkPreference) darkPreference.addEventListener('change', () => { applyTheme(darkPreference.checked ? 'dark' : 'light'); });

  /* ---------- Sidebar ---------- */
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  function toggleSidebar(open) {
    document.body.classList.toggle('sidebar-open', open);
  }
  if (sidebarToggle) sidebarToggle.addEventListener('click', () => toggleSidebar(true));
  if (sidebarOverlay) sidebarOverlay.addEventListener('click', () => toggleSidebar(false));

  /* ---------- Toasts ---------- */
  window.toast = function (message, type) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const el = document.createElement('div');
    el.className = 'toast toast-' + (type || 'info');
    const iconMap = { error: 'fa-circle-exclamation', success: 'fa-circle-check', info: 'fa-circle-info' };
    el.innerHTML =
      '<i class="fa-solid ' + (iconMap[type || 'info'] || 'fa-circle-info') + '"></i>' +
      '<span></span><button class="toast-close">&times;</button>';
    el.querySelector('span').textContent = message;
    el.querySelector('.toast-close').addEventListener('click', () => el.remove());
    container.appendChild(el);
    setTimeout(() => { if (el.parentNode) el.remove(); }, 6000);
  };

  /* ---------- Drag & drop uploads ---------- */
  function setupDropzone(dz, fileInput, hiddenInput, previewEl, nameEl, sizeEl, removeEl, progressEl, btn, ext) {
    if (!dz) return;
    dz.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) handleFile(fileInput.files[0]);
    });
    ['dragenter', 'dragover'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add('dragover'); }));
    ['dragleave', 'drop'].forEach(ev => dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove('dragover'); }));
    dz.addEventListener('drop', e => {
      const f = e.dataTransfer && e.dataTransfer.files[0];
      if (f) handleFile(f);
    });
    if (removeEl) removeEl.addEventListener('click', e => {
      e.stopPropagation();
      fileInput.value = '';
      if (hiddenInput) hiddenInput.value = '';
      previewEl.style.display = 'none';
      if (btn) btn.disabled = true;
    });

    function handleFile(f) {
      if (!f) return;
      const okExt = (ext || '.pdf,.txt,.doc,.docx,.jpg,.jpeg,.png').split(',').map(s => s.replace('.', '').toLowerCase());
      const fext = (f.name.split('.').pop() || '').toLowerCase();
      if (okExt.indexOf(fext) === -1) {
        toast('Unsupported file type. Allowed: ' + okExt.join(', ').toUpperCase(), 'error');
        return;
      }
      if (f.size > 10 * 1024 * 1024) { toast('File too large (max 10 MB).', 'error'); return; }
      if (hiddenInput) {
        try {
          const transfer = new DataTransfer();
          transfer.items.add(f);
          hiddenInput.files = transfer.files;
        } catch (e) {
          toast('This browser cannot attach the selected file. Please try the file picker again.', 'error');
          return;
        }
      }
      if (nameEl) nameEl.textContent = f.name;
      if (sizeEl) sizeEl.textContent = (f.size / 1024 / 1024).toFixed(2) + ' MB';
      previewEl.style.display = 'block';
      if (btn) btn.disabled = false;
      if (progressEl) {
        progressEl.style.width = '0%';
        let i = 0;
        const timer = setInterval(() => {
          i = Math.min(90, i + (i * i + 3) / 6);
          progressEl.style.width = i + '%';
        }, 120);
        window.__progressTimer = timer;
        setTimeout(() => { clearInterval(timer); progressEl.style.width = '100%'; }, 1400);
      }
    }
  }

  const reportDz = document.getElementById('dropzone');
  const reportHidden = document.getElementById('fileInputHidden');
  if (reportDz) {
    setupDropzone(
      reportDz, document.getElementById('fileInput'), reportHidden,
      document.getElementById('dzPreview'), document.getElementById('previewName'),
      document.getElementById('previewSize'), document.getElementById('previewRemove'),
      document.getElementById('uploadProgress'), document.getElementById('analyzeBtn'),
      '.pdf,.txt,.doc,.docx,.jpg,.jpeg,.png'
    );
  }

  const skinDz = document.getElementById('dropzoneSkin');
  if (skinDz) {
    setupDropzone(
      skinDz, document.getElementById('fileInputSkin'), document.getElementById('fileInputSkinHidden'),
      document.getElementById('dzPreviewSkin'), document.getElementById('previewNameSkin'),
      document.getElementById('previewSizeSkin'), document.getElementById('previewRemoveSkin'),
      null, document.getElementById('skinAnalyzeBtn'),
      '.jpg,.jpeg,.png'
    );
  }

  /* ---------- Form loaders ---------- */
  ['uploadForm', 'skinForm', 'dietForm'].forEach(id => {
    const form = document.getElementById(id);
    if (!form) return;
    form.addEventListener('submit', () => {
      const loader = document.getElementById('pageLoader');
      if (loader) loader.classList.add('show');
      if (window.__progressTimer) clearInterval(window.__progressTimer);
    });
  });

  /* ---------- Delete confirmation ---------- */
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
      if (!window.confirm(form.getAttribute('data-confirm'))) {
        e.preventDefault();
        e.stopImmediatePropagation();
      }
    });
  });

  /* ---------- Chat ---------- */
  const chatFab = document.getElementById('chatFab');
  const chatWidget = document.getElementById('chatWidget');
  const chatClose = document.getElementById('chatClose');
  const chatBody = document.getElementById('chatBody');
  const chatInput = document.getElementById('chatInput');
  const chatSend = document.getElementById('chatSend');
  const openChatFromSidebar = document.getElementById('openChatFromSidebar');
  const voiceInputBtn = document.getElementById('voiceInputBtn');
  const voiceStopBtn = document.getElementById('voiceStopBtn');
  const voicePlayBtn = document.getElementById('voicePlayBtn');
  const voicePauseBtn = document.getElementById('voicePauseBtn');
  const voiceStatus = document.getElementById('voiceStatus');
  let lastDiaReply = '';
  let recognition = null;

  const speechLocales = { en: 'en-IN', kn: 'kn-IN', te: 'te-IN', hi: 'hi-IN' };
  function selectedSpeechLocale() { return speechLocales[window.__LANGUAGE__] || 'en-IN'; }
  function detectTypedLanguage(text) { /*
    if (/[80-F]/.test(text)) return 'kn';
    if (/[00-7F]/.test(text)) return 'te';
    if (/[	00-	7F]/.test(text)) return 'hi';
     if (/[\u0C80-\u0CFF]/.test(text)) return 'kn';
     if (/[\u0C00-\u0C7F]/.test(text)) return 'te';
     if (/[\u0900-\u097F]/.test(text)) return 'hi';
    */
    if (/[^\u0000-\u007F]/.test(text)) return detectTypedLanguageSafe(text);
    return window.__LANGUAGE__ || 'en';
  }
  function setVoiceStatus(message) { if (voiceStatus) voiceStatus.textContent = message; }

  const resultSpeech = { utterance: null, button: null, text: '' };
  const resultLanguageText = {
    en: {
      hear: '🔊 Hear This Result', pause: '⏸ Pause', resume: '▶ Resume', stop: '⏹ Stop', simple: "🤔 I Don't Understand",
      title: '🧠 Dia Simple Explanation', what: 'What is it?', result: 'Your Result', range: 'Report Range', meaning: '💡 Simple meaning', why: '👀 Why did Dia flag it?', discuss: '🩺 What should I discuss?', hearSimple: '🔊 Hear Explanation', translate: '🌐 Translate', ask: '💬 Ask Dia About This', speaking: 'Dia is speaking...', unavailable: 'Voice for this language is not available on this device. You can still read the explanation.', normal: 'within the report range', outside: 'outside the report range', reason: 'The detected value is outside the reference range shown in the report.', discussText: 'Consider discussing this result, its context, and whether monitoring is appropriate with a healthcare professional.'
    },
    kn: {
      hear: '🔊 ಈ ಫಲಿತಾಂಶವನ್ನು ಕೇಳಿ', pause: '⏸ ವಿರಾಮ', resume: '▶ ಮುಂದುವರಿಸಿ', stop: '⏹ ನಿಲ್ಲಿಸಿ', simple: '🤔 ನನಗೆ ಅರ್ಥವಾಗುತ್ತಿಲ್ಲ',
      title: '🧠 ಡಿಯಾ ಸರಳ ವಿವರಣೆ', what: 'ಇದು ಏನು?', result: 'ನಿಮ್ಮ ಫಲಿತಾಂಶ', range: 'ವರದಿ ಮಿತಿ', meaning: '💡 ಸರಳ ಅರ್ಥ', why: '👀 ಡಿಯಾ ಇದನ್ನು ಏಕೆ ಗುರುತಿಸಿದೆ?', discuss: '🩺 ಏನು ಚರ್ಚಿಸಬೇಕು?', hearSimple: '🔊 ವಿವರಣೆಯನ್ನು ಕೇಳಿ', translate: '🌐 ಭಾಷಾಂತರಿಸಿ', ask: '💬 ಈ ವಿಷಯವನ್ನು ಡಿಯಾಗೆ ಕೇಳಿ', speaking: 'ಡಿಯಾ ಮಾತನಾಡುತ್ತಿದೆ...', unavailable: 'ಈ ಸಾಧನದಲ್ಲಿ ಈ ಭಾಷೆಯ ಧ್ವನಿ ಲಭ್ಯವಿಲ್ಲ. ನೀವು ವಿವರಣೆಯನ್ನು ಓದಬಹುದು.', normal: 'ವರದಿ ಮಿತಿಯೊಳಗೆ', outside: 'ವರದಿ ಮಿತಿಯ ಹೊರಗೆ', reason: 'ಪತ್ತೆಯಾದ ಮೌಲ್ಯವು ವರದಿಯಲ್ಲಿ ತೋರಿಸಿರುವ ಉಲ್ಲೇಖ ಮಿತಿಯ ಹೊರಗಿದೆ.', discussText: 'ಈ ಫಲಿತಾಂಶ, ಅದರ ಸಂದರ್ಭ ಮತ್ತು ಮೇಲ್ವಿಚಾರಣೆ ಅಗತ್ಯವಿದೆಯೇ ಎಂಬುದನ್ನು ಆರೋಗ್ಯ ವೃತ್ತಿಪರರೊಂದಿಗೆ ಚರ್ಚಿಸಿ.'
    },
    te: {
      hear: '🔊 ఈ ఫలితాన్ని వినండి', pause: '⏸ విరామం', resume: '▶ కొనసాగించండి', stop: '⏹ ఆపండి', simple: '🤔 నాకు అర్థం కాలేదు',
      title: '🧠 డియా సరళ వివరణ', what: 'ఇది ఏమిటి?', result: 'మీ ఫలితం', range: 'నివేదిక పరిధి', meaning: '💡 సులభమైన అర్థం', why: '👀 డియా దీన్ని ఎందుకు గుర్తించింది?', discuss: '🩺 ఏమి చర్చించాలి?', hearSimple: '🔊 వివరణ వినండి', translate: '🌐 అనువదించండి', ask: '💬 దీని గురించి డియాను అడగండి', speaking: 'డియా మాట్లాడుతోంది...', unavailable: 'ఈ భాషకు వాయిస్ ఈ పరికరంలో అందుబాటులో లేదు. మీరు వివరణను చదవవచ్చు.', normal: 'నివేదిక పరిధిలో', outside: 'నివేదిక పరిధికి వెలుపల', reason: 'గుర్తించిన విలువ నివేదికలో చూపించిన రిఫరెన్స్ పరిధికి వెలుపల ఉంది.', discussText: 'ఈ ఫలితం, దాని సందర్భం మరియు పర్యవేక్షణ అవసరమా అనే విషయాన్ని ఆరోగ్య నిపుణుడితో చర్చించండి.'
    },
    hi: {
      hear: '🔊 यह परिणाम सुनें', pause: '⏸ रोकें', resume: '▶ फिर शुरू करें', stop: '⏹ बंद करें', simple: '🤔 मुझे समझ नहीं आया',
      title: '🧠 डिया का सरल विवरण', what: 'यह क्या है?', result: 'आपका परिणाम', range: 'रिपोर्ट सीमा', meaning: '💡 सरल अर्थ', why: '👀 डिया ने इसे क्यों चिन्हित किया?', discuss: '🩺 क्या चर्चा करें?', hearSimple: '🔊 विवरण सुनें', translate: '🌐 अनुवाद करें', ask: '💬 इसके बारे में डिया से पूछें', speaking: 'डिया बोल रही है...', unavailable: 'इस भाषा की आवाज इस डिवाइस पर उपलब्ध नहीं है। आप विवरण पढ़ सकते हैं।', normal: 'रिपोर्ट सीमा में', outside: 'रिपोर्ट सीमा से बाहर', reason: 'मिला हुआ मान रिपोर्ट में दी गई संदर्भ सीमा से बाहर है।', discussText: 'इस परिणाम, इसके संदर्भ और निगरानी की जरूरत पर स्वास्थ्य पेशेवर से चर्चा करें।'
    }
  };
  function resultCopy() { return resultLanguageText[window.__LANGUAGE__] || resultLanguageText.en; }
  function resultValue(item) { return item.is_bp ? (item.value || '—') : (item.value + ' ' + (item.unit || '')).trim(); }
  function resultRange(item) { return refText(item); }
  function simpleTestMeaning(key, lang) {
    const meanings = {
      en: { hba1c: 'HbA1c is a blood test that gives an idea of average blood sugar over the previous few months.', glucose: 'Glucose is the sugar in your blood that your body uses for energy.', 'fasting glucose': 'Fasting glucose is a blood sugar measurement taken after the reported fasting period.', ldl: 'LDL is often called bad cholesterol. Higher LDL can be associated with cholesterol buildup in blood vessels.', hdl: 'HDL is often called good cholesterol and helps carry cholesterol away from the blood vessels.', 'total cholesterol': 'Total cholesterol is the overall amount of cholesterol measured in your blood.', triglycerides: 'Triglycerides are a type of fat measured in the blood.', hemoglobin: 'Hemoglobin is a part of red blood cells that carries oxygen.', 'vitamin d': 'Vitamin D is a nutrient that supports bones and other body functions.', tsh: 'TSH is a hormone signal related to thyroid function.', creatinine: 'Creatinine is a waste product measured alongside other information about kidney function.', alt: 'ALT is an enzyme measured in the blood.', ast: 'AST is an enzyme measured in the blood.', 'blood pressure': 'Blood pressure is the force of blood moving through your blood vessels.' },
      kn: { hba1c: 'HbA1c ಹಿಂದಿನ ಕೆಲವು ತಿಂಗಳ ಸರಾಸರಿ ರಕ್ತದಲ್ಲಿನ ಸಕ್ಕರೆಯ ಬಗ್ಗೆ ತಿಳಿಸುವ ರಕ್ತ ಪರೀಕ್ಷೆ.', glucose: 'ಗ್ಲೂಕೋಸ್ ದೇಹವು ಶಕ್ತಿಗಾಗಿ ಬಳಸುವ ರಕ್ತದಲ್ಲಿನ ಸಕ್ಕರೆ.', 'fasting glucose': 'ಫಾಸ್ಟಿಂಗ್ ಗ್ಲೂಕೋಸ್ ಉಪವಾಸದ ನಂತರದ ರಕ್ತದಲ್ಲಿನ ಸಕ್ಕರೆ ಅಳತೆ.', ldl: 'LDL ಅನ್ನು ಸಾಮಾನ್ಯವಾಗಿ ಕೆಟ್ಟ ಕೊಲೆಸ್ಟ್ರಾಲ್ ಎಂದು ಕರೆಯುತ್ತಾರೆ. ಹೆಚ್ಚಿನ LDL ರಕ್ತನಾಳಗಳಲ್ಲಿ ಕೊಲೆಸ್ಟ್ರಾಲ್ ಜಮೆಯಾಗುವುದಕ್ಕೆ ಸಂಬಂಧಿಸಿರಬಹುದು.', hdl: 'HDL ಅನ್ನು ಸಾಮಾನ್ಯವಾಗಿ ಒಳ್ಳೆಯ ಕೊಲೆಸ್ಟ್ರಾಲ್ ಎಂದು ಕರೆಯುತ್ತಾರೆ.', 'total cholesterol': 'ಒಟ್ಟು ಕೊಲೆಸ್ಟ್ರಾಲ್ ರಕ್ತದಲ್ಲಿನ ಒಟ್ಟು ಕೊಲೆಸ್ಟ್ರಾಲ್ ಅಳತೆ.', triglycerides: 'ಟ್ರೈಗ್ಲಿಸರೈಡ್‌ಗಳು ರಕ್ತದಲ್ಲಿನ ಒಂದು ರೀತಿಯ ಕೊಬ್ಬು.', hemoglobin: 'ಹಿಮೋಗ್ಲೋಬಿನ್ ಕೆಂಪು ರಕ್ತಕಣಗಳಲ್ಲಿದ್ದು ಆಮ್ಲಜನಕವನ್ನು ಸಾಗಿಸುತ್ತದೆ.', 'vitamin d': 'ವಿಟಮಿನ್ D ಎಲುಬುಗಳು ಮತ್ತು ದೇಹದ ಇತರ ಕಾರ್ಯಗಳಿಗೆ ಸಹಾಯ ಮಾಡುತ್ತದೆ.', tsh: 'TSH ಥೈರಾಯ್ಡ್ ಕಾರ್ಯಕ್ಕೆ ಸಂಬಂಧಿಸಿದ ಹಾರ್ಮೋನ್ ಸಂಕೇತ.', creatinine: 'ಕ್ರಿಯಾಟಿನಿನ್ ಮೂತ್ರಪಿಂಡದ ಕಾರ್ಯದ ಇತರ ಮಾಹಿತಿಯೊಂದಿಗೆ ಅಳೆಯುವ ತ್ಯಾಜ್ಯ ಪದಾರ್ಥ.', alt: 'ALT ರಕ್ತದಲ್ಲಿ ಅಳೆಯುವ ಎಂಜೈಮ್.', ast: 'AST ರಕ್ತದಲ್ಲಿ ಅಳೆಯುವ ಎಂಜೈಮ್.', 'blood pressure': 'ರಕ್ತದೊತ್ತಡವು ರಕ್ತನಾಳಗಳಲ್ಲಿ ಹರಿಯುವ ರಕ್ತದ ಒತ್ತಡ.' },
      te: { hba1c: 'HbA1c గత కొన్ని నెలల సగటు రక్త చక్కెర గురించి తెలియజేసే రక్త పరీక్ష.', glucose: 'గ్లూకోజ్ శరీరం శక్తి కోసం ఉపయోగించే రక్తంలోని చక్కెర.', 'fasting glucose': 'ఫాస్టింగ్ గ్లూకోజ్ అనేది ఉపవాసం తర్వాత తీసుకున్న రక్త చక్కెర కొలత.', ldl: 'LDL ను సాధారణంగా చెడు కొలెస్ట్రాల్ అంటారు. ఎక్కువ LDL రక్తనాళాల్లో కొలెస్ట్రాల్ పేరుకుపోవడంతో సంబంధం కలిగి ఉండవచ్చు.', hdl: 'HDL ను సాధారణంగా మంచి కొలెస్ట్రాల్ అంటారు.', 'total cholesterol': 'టోటల్ కొలెస్ట్రాల్ రక్తంలో ఉన్న మొత్తం కొలెస్ట్రాల్ కొలత.', triglycerides: 'ట్రైగ్లిసరైడ్లు రక్తంలో కొలిచే ఒక రకమైన కొవ్వు.', hemoglobin: 'హీమోగ్లోబిన్ ఎర్ర రక్త కణాల్లో ఉండి ఆక్సిజన్‌ను తీసుకెళ్తుంది.', 'vitamin d': 'విటమిన్ D ఎముకలు మరియు శరీరంలోని ఇతర పనులకు సహాయపడుతుంది.', tsh: 'TSH థైరాయిడ్ పనితీరుకు సంబంధించిన హార్మోన్ సంకేతం.', creatinine: 'క్రియాటినిన్ మూత్రపిండాల పనితీరుకు సంబంధించిన ఇతర సమాచారంతో కొలిచే వ్యర్థ పదార్థం.', alt: 'ALT రక్తంలో కొలిచే ఒక ఎంజైమ్.', ast: 'AST రక్తంలో కొలిచే ఒక ఎంజైమ్.', 'blood pressure': 'బ్లడ్ ప్రెషర్ రక్తనాళాల్లో ప్రవహించే రక్తం యొక్క ఒత్తిడి.' },
      hi: { hba1c: 'HbA1c एक रक्त जांच है जो पिछले कुछ महीनों के औसत रक्त शर्करा का अंदाजा देती है।', glucose: 'ग्लूकोज रक्त में मौजूद शर्करा है जिसका शरीर ऊर्जा के लिए उपयोग करता है।', 'fasting glucose': 'फास्टिंग ग्लूकोज उपवास के बाद मापी गई रक्त शर्करा है।', ldl: 'LDL को अक्सर खराब कोलेस्ट्रॉल कहा जाता है। अधिक LDL रक्त वाहिकाओं में कोलेस्ट्रॉल जमा होने से संबंधित हो सकता है।', hdl: 'HDL को अक्सर अच्छा कोलेस्ट्रॉल कहा जाता है।', 'total cholesterol': 'कुल कोलेस्ट्रॉल रक्त में मापी गई कुल कोलेस्ट्रॉल मात्रा है।', triglycerides: 'ट्राइग्लिसराइड रक्त में मापी जाने वाली एक प्रकार की वसा है।', hemoglobin: 'हीमोग्लोबिन लाल रक्त कोशिकाओं का हिस्सा है जो ऑक्सीजन ले जाता है।', 'vitamin d': 'विटामिन D हड्डियों और शरीर के अन्य कामों में मदद करता है।', tsh: 'TSH थायरॉइड के काम से जुड़ा हार्मोन संकेत है।', creatinine: 'क्रिएटिनिन एक अपशिष्ट पदार्थ है जिसे किडनी की जानकारी के साथ देखा जाता है।', alt: 'ALT रक्त में मापा जाने वाला एक एंजाइम है।', ast: 'AST रक्त में मापा जाने वाला एक एंजाइम है।', 'blood pressure': 'ब्लड प्रेशर रक्त वाहिकाओं में बहते रक्त का दबाव है।' }
    };
    return (meanings[lang] || meanings.en)[key] || 'This is a laboratory measurement from your report.';
  }
  function speakResult(text, button) {
    if (!('speechSynthesis' in window)) { toast(resultCopy().unavailable, 'info'); return; }
    window.speechSynthesis.cancel();
    const voices = window.speechSynthesis.getVoices();
    const prefix = (speechLocales[window.__LANGUAGE__] || 'en-IN').split('-')[0];
    const voice = voices.find(item => item.lang && item.lang.toLowerCase().startsWith(prefix));
    if (!voice && prefix !== 'en') { toast(resultCopy().unavailable, 'info'); }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = speechLocales[window.__LANGUAGE__] || 'en-IN';
    if (voice) utterance.voice = voice;
    resultSpeech.utterance = utterance;
    resultSpeech.button = button;
    resultSpeech.text = text;
    if (button) { button.disabled = true; button.classList.add('speaking'); }
    document.body.classList.add('dia-speaking');
    utterance.onend = utterance.onerror = () => { if (button) { button.disabled = false; button.classList.remove('speaking'); } document.body.classList.remove('dia-speaking'); resultSpeech.utterance = null; };
    window.speechSynthesis.speak(utterance);
  }
  function explainResult(item) {
    const lang = window.__LANGUAGE__ || 'en';
    const copy = resultCopy();
    const value = resultValue(item);
    const range = resultRange(item);
    const status = item.status;
    const meaning = simpleTestMeaning(item.key, lang);
    const isNormal = status === 'NORMAL';
    if (lang === 'kn') return `ನಿಮ್ಮ ${item.test} ಮೌಲ್ಯವು ${value} ಆಗಿದೆ. ಇದು ${isNormal ? 'ನಿಮ್ಮ ವರದಿಯಲ್ಲಿ ನೀಡಿರುವ ಮಿತಿಯೊಳಗೆ ಇದೆ' : 'ನಿಮ್ಮ ವರದಿಯಲ್ಲಿ ನೀಡಿರುವ ಮಿತಿಯ ಹೊರಗಿದೆ'} (${range}). ${meaning} ${isNormal ? 'ಇದು ಸಾಮಾನ್ಯವಾಗಿ ಕಾಣುತ್ತದೆ.' : 'ಇದು ಸರಾಸರಿ ಫಲಿತಾಂಶದ ಬಗ್ಗೆ ಹೆಚ್ಚು ಗಮನಿಸಬೇಕಾದ ವಿಷಯವನ್ನು ಸೂಚಿಸಬಹುದು. ಆರೋಗ್ಯ ವೃತ್ತಿಪರರೊಂದಿಗೆ ಚರ್ಚಿಸಿ.'}`;
    if (lang === 'te') return `మీ ${item.test} విలువ ${value}. ఇది మీ నివేదికలో చూపించిన పరిధి ${range} ${isNormal ? 'లో ఉంది' : 'కు వెలుపల ఉంది'}. ${meaning} ${isNormal ? 'ఇది సాధారణంగా కనిపిస్తుంది.' : 'ఇది మరింత చర్చించాల్సిన విషయాన్ని సూచించవచ్చు. ఆరోగ్య నిపుణుడితో చర్చించండి.'}`;
    if (lang === 'hi') return `आपका ${item.test} ${value} है। यह आपकी रिपोर्ट की सीमा ${range} ${isNormal ? 'में है' : 'से बाहर है'}। ${meaning} ${isNormal ? 'यह सामान्य दिखता है।' : 'यह आगे चर्चा किए जाने वाले विषय का संकेत दे सकता है। स्वास्थ्य पेशेवर से चर्चा करें।'}`;
    return `Your ${item.test} is ${value}, which is ${isNormal ? 'within' : 'outside'} the reference range shown in your report (${range}). ${meaning} ${isNormal ? 'This appears within the report range.' : 'This may indicate an area to discuss with a healthcare professional.'}`;
  }
  function buildSimpleCard(item, card) {
    const copy = resultCopy();
    const panel = document.createElement('div'); panel.className = 'simple-explanation-card';
    panel.innerHTML = `<h3>${esc(copy.title)}</h3><div class="simple-detail"><strong>${esc(copy.what)}</strong><p>${esc(simpleTestMeaning(item.key, window.__LANGUAGE__ || 'en'))}</p></div><div class="simple-detail"><strong>${esc(copy.result)}</strong><p>${esc(resultValue(item))}</p></div><div class="simple-detail"><strong>${esc(copy.range)}</strong><p>${esc(resultRange(item))}</p></div><div class="simple-detail"><strong>${esc(copy.why)}</strong><p>${esc(item.status === 'NORMAL' ? copy.normal : copy.reason)}</p></div><div class="simple-detail"><strong>${esc(copy.meaning)}</strong><p>${esc(explainResult(item))}</p></div><div class="simple-detail"><strong>${esc(copy.discuss)}</strong><p>${esc(copy.discussText)}</p></div><div class="simple-actions"><button type="button" class="btn btn-secondary simple-hear">${esc(copy.hearSimple)}</button><button type="button" class="btn btn-outline simple-pause">${esc(copy.pause)}</button><button type="button" class="btn btn-outline simple-resume">${esc(copy.resume)}</button><button type="button" class="btn btn-outline simple-stop">${esc(copy.stop)}</button><select class="simple-translate" aria-label="${esc(copy.translate)}"><option value="en">English</option><option value="kn">ಕನ್ನಡ</option><option value="te">తెలుగు</option><option value="hi">हिन्दी</option></select><button type="button" class="btn btn-outline simple-ask">${esc(copy.ask)}</button><span class="simple-speaking" aria-live="polite"></span></div>`;
    panel.querySelector('.simple-hear').addEventListener('click', event => speakResult(explainResult(item), event.currentTarget));
    panel.querySelector('.simple-pause').addEventListener('click', () => { if ('speechSynthesis' in window) window.speechSynthesis.pause(); });
    panel.querySelector('.simple-resume').addEventListener('click', () => { if ('speechSynthesis' in window) window.speechSynthesis.resume(); });
    panel.querySelector('.simple-stop').addEventListener('click', () => { if ('speechSynthesis' in window) { window.speechSynthesis.cancel(); document.body.classList.remove('dia-speaking'); } });
    panel.querySelector('.simple-translate').value = window.__LANGUAGE__ || 'en';
    panel.querySelector('.simple-translate').addEventListener('change', event => { window.__LANGUAGE__ = event.target.value; const replacement = buildSimpleCard(item, card); panel.replaceWith(replacement); });
    panel.querySelector('.simple-ask').addEventListener('click', () => { openChat(); chatInput.value = `Explain my ${item.test} result of ${resultValue(item)} in simple language.`; chatInput.focus(); });
    return panel;
  }

  function detectTypedLanguageSafe(text) {
    if (/[\u0C80-\u0CFF]/.test(text)) return 'kn';
    if (/[\u0C00-\u0C7F]/.test(text)) return 'te';
    if (/[\u0900-\u097F]/.test(text)) return 'hi';
    return window.__LANGUAGE__ || 'en';
  }

  function speak(text) {
    if (!('speechSynthesis' in window)) { setVoiceStatus('Voice output is not supported in this browser.'); return; }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = selectedSpeechLocale();
    window.speechSynthesis.speak(utterance);
    setVoiceStatus('Playing response');
  }
  function startRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) { setVoiceStatus('Voice input is not supported in this browser. You can type your question instead.'); return; }
    if (recognition) recognition.stop();
    recognition = new SpeechRecognition();
    recognition.lang = selectedSpeechLocale();
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setVoiceStatus('Listening…');
    recognition.onresult = event => { chatInput.value = event.results[0][0].transcript; setVoiceStatus('Voice captured. Press send.'); };
    recognition.onerror = () => setVoiceStatus('Voice input was unavailable. You can type your question instead.');
    recognition.onend = () => { if (voiceInputBtn) voiceInputBtn.classList.remove('is-listening'); };
    if (voiceInputBtn) voiceInputBtn.classList.add('is-listening');
    recognition.start();
  }
  if (voiceInputBtn) voiceInputBtn.addEventListener('click', startRecognition);
  if (voiceStopBtn) voiceStopBtn.addEventListener('click', () => { if (recognition) recognition.stop(); setVoiceStatus('Voice input stopped'); });
  if (voicePauseBtn) voicePauseBtn.addEventListener('click', () => { if ('speechSynthesis' in window) { window.speechSynthesis.cancel(); setVoiceStatus('Audio stopped'); } });
  if (voicePlayBtn) voicePlayBtn.addEventListener('click', () => { if (lastDiaReply) speak(lastDiaReply); else setVoiceStatus('Ask a question first.'); });

  function openChat() {
    if (chatFab) chatFab.classList.add('open');
    if (chatWidget) chatWidget.classList.add('open');
    if (chatInput) setTimeout(() => chatInput.focus(), 250);
  }
  function closeChat() {
    if (chatFab) chatFab.classList.remove('open');
    if (chatWidget) chatWidget.classList.remove('open');
  }
  if (chatFab) chatFab.addEventListener('click', () => {
    chatWidget.classList.contains('open') ? closeChat() : openChat();
  });
  if (chatClose) chatClose.addEventListener('click', closeChat);
  if (openChatFromSidebar) openChatFromSidebar.addEventListener('click', openChat);
  document.querySelectorAll('[data-open-chat]').forEach(el => el.addEventListener('click', openChat));

  function addQuickQuestions() {
    if (!chatBody) return;
    const bar = document.createElement('div');
    bar.className = 'quick-qs';
    ['Explain my report', 'Show abnormal results', 'What changed?', 'Explain simply', 'Prepare doctor questions', 'Read my report']
      .forEach(q => {
        const b = document.createElement('button');
        b.textContent = q;
        b.addEventListener('click', () => sendChat(q));
        bar.appendChild(b);
      });
    chatBody.appendChild(bar);
  }
  addQuickQuestions();

  function pushMsg(text, who, typing) {
    const wrap = document.createElement('div');
    wrap.className = 'chat-msg ' + who + (typing ? ' chat-typing' : '');
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble';
    if (typing) {
      bubble.innerHTML = '<span></span><span></span><span></span>';
    } else {
      bubble.textContent = text;
    }
    wrap.appendChild(bubble);
    chatBody.appendChild(wrap);
    chatBody.scrollTop = chatBody.scrollHeight;
    return wrap;
  }

  function sendChat(text) {
    if (!text || !text.trim()) return;
    pushMsg(text.trim(), 'user');
    const typingEl = pushMsg('', 'bot', true);
    chatInput.value = '';

    fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text.trim(), language: detectTypedLanguageSafe(text.trim()) }),
    })
      .then(r => r.json())
      .then(data => {
        if (typingEl.parentNode) typingEl.remove();
        lastDiaReply = data.reply || 'I could not process that. Please try again.';
        pushMsg(lastDiaReply, 'bot');
      })
      .catch(() => {
        if (typingEl.parentNode) typingEl.remove();
        pushMsg('Something went wrong on the server. Please try again.', 'bot');
      });
  }

  if (chatSend) chatSend.addEventListener('click', () => sendChat(chatInput.value));
  if (chatInput) {
    chatInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(chatInput.value); }
    });
  }
  document.querySelectorAll('[data-talk-report]').forEach(button => button.addEventListener('click', () => { openChat(); chatInput.value = 'Explain my report simply'; chatInput.focus(); }));
  document.querySelectorAll('[data-speak-report]').forEach(button => button.addEventListener('click', () => { openChat(); if (lastDiaReply) speak(lastDiaReply); else sendChat('Explain my report simply'); }));

  /* ---------- Dashboard rendering ---------- */
  function renderDashboard() {
    const analysis = window.__ANALYSIS__;
    if (!analysis) return;
    const existingResults = document.querySelector('#resultsTable tbody');
    if (existingResults && existingResults.children.length) return;
    const patient = window.__PATIENT__ || {};

    /* Key findings banner */
    const kf = document.getElementById('keyFindings');
    if (kf) {
      const abnormal = analysis.filter(a => ['HIGH', 'LOW', 'BORDERLINE'].indexOf(a.status) !== -1);
      if (abnormal.length) {
        kf.innerHTML = '<i class="fa-solid fa-bell"></i> <b>' + abnormal.length + ' value(s)</b> flagged outside the reference range: <b>' +
          abnormal.map(a => a.test).join(', ') + '</b>. These are not diagnoses — discuss them with your healthcare professional.';
      } else {
        kf.innerHTML = '<i class="fa-solid fa-circle-check"></i> All detected values fall within the reference ranges available. Great baseline — keep your doctor in the loop.';
      }
    }

    /* Abnormal grid */
    const grid = document.getElementById('abnormalGrid');
    const noAbn = document.getElementById('noAbnormalHint');
    if (grid) {
      const abnormal = analysis.filter(a => ['HIGH', 'LOW', 'BORDERLINE'].indexOf(a.status) !== -1);
      if (abnormal.length === 0) { grid.style.display = 'none'; if (noAbn) noAbn.style.display = 'block'; }
      abnormal.forEach(a => {
        const card = document.createElement('div');
        card.className = 'abnormal-card state-' + a.status;
        const ref = refText(a);
        const val = a.is_bp ? (a.value || '—') : (a.value + ' ' + (a.unit || '')).trim();
        card.innerHTML =
          '<h4>' + esc(a.test) + ' <span class="badge badge-' + badgeClass(a.status) + '">' + esc(a.status) + '</span></h4>' +
          '<div class="value-line">' + esc(val) + '</div>' +
          '<div class="ref-line">Ref: ' + esc(ref) + '</div>' +
          '<p class="explain">' + esc(a.explanation || '') + '</p>' +
          '<div class="result-actions"><button class="why-button" type="button">🔍 Why did Dia flag this?</button><button class="simple-trigger" type="button">' + esc(resultCopy().simple) + '</button><button class="result-hear" type="button">' + esc(resultCopy().hear) + '</button></div>' +
          '<div class="why-panel" hidden><p><strong>What it measures:</strong> ' + esc(measureMeaning(a.key)) + '</p>' +
          '<p><strong>Why it is outside the range:</strong> The recorded value is ' + esc(a.status.toLowerCase()) + ' compared with ' + esc(ref) + '.</p>' +
          '<p><strong>Possible general significance:</strong> ' + esc(a.possible_significance || a.explanation || 'This may indicate an area to discuss with a healthcare professional.') + '</p>' +
          '<p><strong>Discuss with a professional:</strong> Ask whether follow-up testing, context, or monitoring is appropriate for you.</p></div>';
        card.querySelector('.why-button').addEventListener('click', function () {
          const panel = card.querySelector('.why-panel');
          panel.hidden = !panel.hidden;
          this.textContent = panel.hidden ? 'Why is this abnormal?' : 'Hide explanation';
        });
        card.querySelector('.result-hear').addEventListener('click', event => speakResult(explainResult(a), event.currentTarget));
        card.querySelector('.simple-trigger').addEventListener('click', function () {
          let panel = card.querySelector('.simple-explanation-card');
          if (panel) { panel.remove(); return; }
          panel = buildSimpleCard(a, card);
          card.appendChild(panel);
        });
        grid.appendChild(card);
      });
    }

    const trendGrid = document.getElementById('trendGrid');
    const trendData = window.__TRENDS__ || [];
    if (trendGrid) {
      if (!trendData.length) {
        const hint = document.getElementById('noTrendsHint');
        if (hint) hint.style.display = 'block';
      } else if (window.Chart) {
        trendData.forEach((trend, index) => {
          const card = document.createElement('div');
          card.className = 'chart-card trend-card';
          card.innerHTML = '<div class="trend-heading"><h3>' + esc(trend.test) + '</h3><span class="badge badge-blue">' + esc(trend.direction) + '</span></div><div class="chart-box"><canvas id="trend' + index + '"></canvas></div><small>Direction is mathematical only and is not proof of improvement or deterioration.</small>';
          trendGrid.appendChild(card);
          new Chart(card.querySelector('canvas'), {
            type: 'line',
            data: { labels: trend.points.map(point => point.date || point.filename), datasets: [{ label: trend.unit || 'value', data: trend.points.map(point => point.value), borderColor: '#0e7c86', backgroundColor: 'rgba(14,124,134,.12)', fill: true, tension: .3 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false }, x: { grid: { display: false } } } }
          });
        });
      }
    }

    /* Full table */
    const tbody = document.querySelector('#resultsTable tbody');
    if (tbody) {
      analysis.forEach(a => {
        const tr = document.createElement('tr');
        const ref = refText(a);
        const val = a.is_bp ? (a.value || '—') : (a.value + ' ' + (a.unit || '')).trim();
        tr.innerHTML =
          '<td><b>' + esc(a.test) + '</b></td>' +
          '<td>' + esc(val) + '</td>' +
          '<td>' + esc(ref) + '</td>' +
          '<td><span class="badge badge-' + badgeClass(a.status) + '">' + esc(a.status) + '</span></td>' +
          '<td style="font-size:12.5px;color:var(--text-muted)">' + esc(a.using_general ? a.explanation + ' <i>(general reference used)</i>' : a.explanation) + '</td>';
        const actionCell = document.createElement('td');
        actionCell.className = 'result-table-actions';
        actionCell.innerHTML = '<button type="button" class="result-hear table-action">' + esc(resultCopy().hear) + '</button><button type="button" class="simple-trigger table-action">' + esc(resultCopy().simple) + '</button>';
        tr.appendChild(actionCell);
        tbody.appendChild(tr);
        const detailsRow = document.createElement('tr');
        detailsRow.className = 'table-details-row';
        const detailsCell = document.createElement('td'); detailsCell.colSpan = 6;
        detailsRow.appendChild(detailsCell); tbody.appendChild(detailsRow);
        tr.querySelector('.result-hear').addEventListener('click', event => speakResult(explainResult(a), event.currentTarget));
        tr.querySelector('.simple-trigger').addEventListener('click', () => { detailsCell.replaceChildren(detailsCell.firstChild ? null : buildSimpleCard(a, tr)); });
      });
    }

    /* Charts */
    const chartGrid = document.getElementById('chartGrid');
    if (chartGrid && window.Chart) {
      const numeric = analysis.filter(a => typeof a.value === 'number' && !a.is_bp);
      if (numeric.length === 0) { chartGrid.style.display = 'none'; const h = document.getElementById('noChartsHint'); if (h) h.style.display = 'block'; }
      const grouped = {};
      numeric.forEach(a => { (grouped[a.unit || 'no-unit'] = grouped[a.unit || 'no-unit'] || []).push(a); });
      let chartIndex = 0;
      Object.keys(grouped).forEach(unit => {
        const items = grouped[unit].slice(0, 10);
        const card = document.createElement('div');
        card.className = 'chart-card';
        card.innerHTML = '<h3>Labs (' + esc(unit || 'no unit') + ')</h3><div class="chart-box"><canvas id="chart' + chartIndex + '"></canvas></div>';
        chartGrid.appendChild(card);
        const ctx = card.querySelector('canvas').getContext('2d');
        const colors = items.map(i => ({ HIGH: '#c0392b', LOW: '#c0392b', BORDERLINE: '#d35400', NORMAL: '#1e8449', UNKNOWN: '#5b6b7f' })[i.status] || '#0f4c81');
        const labels = items.map(i => i.test);
        const datasets = [{
          label: unit || 'value',
          data: items.map(i => i.value),
          backgroundColor: colors,
          borderRadius: 6,
        }];
        // optional reference range overlays for tests with a range
        items.forEach((i, idx) => {
          if (i.ref_low != null && i.ref_high != null) {
            datasets.push({ label: 'range: ' + i.test, data: items.map((_, j) => j === idx ? i.ref_high - i.ref_low : null), type: 'line', hidden: true });
          }
        });
        new Chart(ctx, {
          type: 'bar',
          data: { labels: labels, datasets: [datasets[0]] },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              y: { beginAtZero: true, grid: { color: 'rgba(120,140,160,.15)' } },
              x: { grid: { display: false } }
            }
          }
        });
        chartIndex++;
      });
    }

    /* Lifestyle guidance */
    const gl = document.getElementById('lifestyleGuidance');
    if (gl) {
      const high = analysis.filter(a => ['HIGH', 'LOW', 'BORDERLINE'].indexOf(a.status) !== -1);
      const items = [];
      if (high.some(a => ['glucose', 'fasting glucose', 'hba1c'].indexOf(a.key) !== -1)) {
        items.push('Reduce added sugar and sugary beverages.');
        items.push('Choose high-fiber foods: vegetables, legumes, whole grains.');
        items.push('Moderate refined carbohydrates; select appropriate protein sources.');
        items.push('Keep regular, moderate physical activity.');
      }
      if (high.some(a => ['ldl', 'total cholesterol', 'triglycerides'].indexOf(a.key) !== -1)) {
        items.push('Emphasize fiber-rich foods, vegetables/fruits and whole grains.');
        items.push('Moderate foods high in saturated and trans fats.');
      }
      if (high.some(a => a.key === 'vitamin d' && a.status !== 'NORMAL')) {
        items.push('Vitamin D below reference: discuss appropriate management with a clinician (no supplement doses prescribed by us).');
      }
      if (!items.length) {
        items.push('Maintain a balanced diet with plenty of vegetables, fruits and whole grains.');
        items.push('Stay active most days, sleep well and stay hydrated.');
      }
      items.push('Discuss your full report with a healthcare professional.');
      gl.innerHTML = '<ul>' + items.map(i => '<li>' + esc(i) + '</li>').join('') + '</ul>';
    }

    /* Doctor questions */
    const dq = document.getElementById('doctorQuestions');
    if (dq) {
      const abn = analysis.filter(a => ['HIGH', 'LOW', 'BORDERLINE'].indexOf(a.status) !== -1);
      const qs = [];
      if (abn.length) {
        qs.push('What do my flagged ' + abn.map(a => a.test).join(', ') + ' results mean, and is any follow-up testing needed?');
      } else {
        qs.push('Is there any part of my report I should pay extra attention to?');
      }
      qs.push('Based on my results, are there lifestyle changes you recommend?');
      ['What do you think of relying on the reference ranges printed on my report?'].forEach(q => qs.push(q));
      dq.innerHTML = qs.map(q => '<li>' + esc(q) + '</li>').join('');
    }
  }

  function refText(a) {
    const unit = a.unit || '';
    if (a.ref_low != null && a.ref_high != null) return a.ref_low + (Number.isInteger(a.ref_low) ? '' : '') + ' – ' + a.ref_high + ' ' + unit;
    if (a.ref_high != null) return '< ' + a.ref_high + ' ' + unit;
    if (a.ref_low != null) return '> ' + a.ref_low + ' ' + unit;
    return 'No reference range';
  }
  function badgeClass(status) {
    return { HIGH: 'red', LOW: 'red', BORDERLINE: 'yellow', NORMAL: 'green', UNKNOWN: 'grey' }[status] || 'blue';
  }
  function measureMeaning(key) {
    return ({
      glucose: 'Blood glucose at the time of the test.',
      'fasting glucose': 'Blood glucose after the reported fasting period.',
      hba1c: 'An estimate of average blood glucose over roughly the previous 2–3 months.',
      ldl: 'Low-density lipoprotein cholesterol.', hdl: 'High-density lipoprotein cholesterol.',
      'total cholesterol': 'The total cholesterol measured in the sample.', triglycerides: 'A type of fat measured in the blood.',
      hemoglobin: 'The oxygen-carrying protein in red blood cells.', 'vitamin d': 'The reported Vitamin D level.',
      tsh: 'Thyroid-stimulating hormone.', creatinine: 'A waste product often considered alongside kidney function.',
      alt: 'Alanine aminotransferase, an enzyme measured in blood.', ast: 'Aspartate aminotransferase, an enzyme measured in blood.',
      'blood pressure': 'The reported systolic and diastolic blood pressure reading.'
    }[key] || 'The laboratory measurement reported by your test.');
  }
  function simpleMeaning(item) {
    const value = item.value + ' ' + (item.unit || '');
    const ref = refText(item);
    return item.test + ': ' + value + '. This is outside the report range (' + ref + '). It may be useful to discuss this result with a healthcare professional.';
  }
  function esc(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  window.__DIA_RENDER_DASHBOARD__ = renderDashboard;
  if (window.__ANALYSIS__) renderDashboard();
  window.addEventListener('dia-dashboard-ready', () => { if (window.__ANALYSIS__) renderDashboard(); });
  document.querySelectorAll('[data-copy-questions]').forEach(button => button.addEventListener('click', () => {
    const text = Array.from(document.querySelectorAll('#doctorQuestions li')).map(item => '- ' + item.textContent).join('\n');
    navigator.clipboard && navigator.clipboard.writeText(text).then(() => toast('Doctor questions copied', 'success')).catch(() => toast('Could not copy questions', 'error'));
  }));
  if (window.__ANALYSIS__) console.log('[Dia Assist] Analysis loaded:', window.__ANALYSIS__);
})();