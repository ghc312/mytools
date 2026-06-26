/**
 * 豆包网页版 - 批量删除当前对话消息（控制台通用版）
 *
 * 配置自动探测：
 *   1. 从 performance API 读取已发出的豆包请求 URL，解析 device_id / web_id 等参数
 *   2. 从 localStorage / sessionStorage 读取
 *   3. 从页面全局 JS 对象递归探测
 *   以上全部自动，无需手动填写任何参数。
 *
 * 使用方法：
 *   1. 打开要清空的对话页面（URL 形如 https://www.doubao.com/chat/xxxxx）
 *   2. F12 → Console（控制台）→ 粘贴运行
 *   3. 等待执行完成，确认弹窗会自动点击
 *
 * 注意：删除不可逆，请确认后再运行！
 */

(async () => {
  'use strict';

  // ========== 用户可配置区域 ==========
  const CONFIG = {
    batchSize:      20,       // 每批删除条数（建议 10~30）
    batchDelay:     500,      // 批次间隔毫秒（避免风控，建议 ≥300）
    scrollDelay:    1500,     // 滚动后等待加载毫秒（初始值）
    maxNoNewRounds: 15,      // 连续多少轮无新消息才终止（给慢响应留足时间）
    retryBaseDelay: 2000,     // 指数退避基础延迟毫秒
    retryMaxDelay:  180000,   // 指数退避最大延迟毫秒（3 分钟）
  };
  // =======================================

  // ========== 自动探测配置（无需手动填写）==========
  const detectConfig = () => {
    const result = {
      device_id:  '',
      web_id:     '',
      pc_version: '',
      aid:        '',
      source:     '',
    };

    // --- 方法1：从 performance API 读取已发出的请求 URL ---
    try {
      const entries = performance.getEntriesByType('resource');
      for (const entry of entries) {
        const url = entry.name;
        if (!url.includes('doubao.com') || !url.includes('?')) continue;
        const params = new URL(url).searchParams;
        const did = params.get('device_id') || params.get('device_id');
        const wid = params.get('web_id')    || params.get('web_id');
        const ver = params.get('pc_version') || params.get('pc_version');
        const aid = params.get('aid')        || params.get('aid');
        if (did || wid) {
          result.device_id  = did || result.device_id;
          result.web_id     = wid || result.web_id;
          result.pc_version = ver || result.pc_version;
          result.aid        = aid || result.aid;
          result.source     = 'performance API';
          console.log('✅ 从网络请求中探测到参数:', { device_id: did, web_id: wid });
          break;
        }
      }
    } catch (e) { console.warn('performance API 读取失败:', e.message); }

    // --- 方法2：从 localStorage / sessionStorage 读取 ---
    const readStorage = (storage) => {
      try {
        for (let i = 0; i < storage.length; i++) {
          const key = storage.key(i);
          const val = storage.getItem(key);
          if (!val) continue;
          try {
            const parsed = JSON.parse(val);
            if (parsed && typeof parsed === 'object') {
              _pickFromObj(parsed, result);
            }
          } catch { /* not JSON, skip */ }
          if (key.toLowerCase().includes('device_id') && val)  result.device_id  = val;
          if (key.toLowerCase().includes('web_id') && val)     result.web_id     = val;
          if (key.toLowerCase().includes('pc_version') && val) result.pc_version = val;
          if (key === 'aid' && val)                           result.aid        = val;
        }
      } catch (e) { /* 跨域或隐私模式可能抛异常 */ }
    };
    if (!result.device_id || !result.web_id) {
      readStorage(localStorage);
      readStorage(sessionStorage);
      if (result.device_id || result.web_id) result.source = 'storage';
    }

    // --- 方法3：从页面全局 JS 对象递归探测 ---
    if (!result.device_id || !result.web_id) {
      const seen = new WeakSet();
      const searchObj = (obj, depth) => {
        if (!obj || typeof obj !== 'object' || seen.has(obj) || depth > 4) return;
        seen.add(obj);
        try {
          for (const [k, v] of Object.entries(obj)) {
            const kl = k.toLowerCase();
            if (kl.includes('device_id')  && v) result.device_id  = String(v);
            if (kl.includes('web_id')     && v) result.web_id     = String(v);
            if (kl.includes('pc_version') && v) result.pc_version = String(v);
            if (kl === 'aid'             && v) result.aid        = String(v);
            if (typeof v === 'object' && v !== null) searchObj(v, depth + 1);
          }
        } catch { /* 某些属性访问可能抛异常 */ }
      };
      const candidateKeys = Object.keys(window).filter(k =>
        k.startsWith('__') || k.startsWith('_DOUBAO') || k.includes('doubao') || k.includes('samantha')
      );
      for (const key of candidateKeys) {
        try { searchObj(window[key], 0); } catch {}
        if (result.device_id && result.web_id) { result.source = `window.${key}`; break; }
      }
    }

    return result;
  };

  const _pickFromObj = (obj, result) => {
    const seen = new WeakSet();
    const walk = (o, depth) => {
      if (!o || typeof o !== 'object' || seen.has(o) || depth > 4) return;
      seen.add(o);
      for (const [k, v] of Object.entries(o)) {
        const kl = k.toLowerCase();
        if (kl.includes('device_id')  && v) result.device_id  = String(v);
        if (kl.includes('web_id')     && v) result.web_id     = String(v);
        if (kl.includes('pc_version') && v) result.pc_version = String(v);
        if (kl === 'aid'             && v) result.aid        = String(v);
        if (typeof v === 'object' && v !== null) walk(v, depth + 1);
      }
    };
    walk(obj);
  };

  const CFG = detectConfig();
  console.log('%c🔍 自动探测配置结果:', 'color:#FF9800;font-weight:bold', CFG);

  const DEVICE_ID  = CFG.device_id  || '';
  const WEB_ID     = CFG.web_id     || '';
  const PC_VERSION  = CFG.pc_version || '3.23.8';
  const AID         = CFG.aid        || '497858';
  const WEB_TAB_ID = crypto.randomUUID();
  // =======================================

  // 从 URL 提取 conversation_id
  const convId = location.pathname.match(/\/chat\/(\d+)/)?.[1];
  if (!convId) {
    console.error('❌ 未识别到对话 ID！请在豆包对话页面运行本脚本。');
    return;
  }
  console.log(`%c对话 ID: ${convId}`, 'color:#4CAF50;font-weight:bold');

  if (!DEVICE_ID || !WEB_ID) {
    console.warn(
      '⚠️ 未能自动探测到 device_id / web_id。\n' +
      '请手动在控制台执行：\n' +
      '  Object.keys(window).filter(k => { try { return window[k] && JSON.stringify(window[k]).includes("device_id"); } catch { return false; } })\n' +
      '找到后告诉我变量名，我帮你更新脚本。'
    );
  }

  // 构建请求 URL
  const buildUrl = (path) => {
    const params = new URLSearchParams({
      version_code:             '20800',
      language:                 'zh',
      device_platform:           'web',
      aid:                      AID,
      real_aid:                 AID,
      pkg_type:                 'release_version',
      device_id:                DEVICE_ID,
      pc_version:               PC_VERSION,
      web_id:                   WEB_ID,
      tea_uuid:                 WEB_ID,
      region:                   'CN',
      sys_region:               'CN',
      samantha_web:             '1',
      web_platform:             'browser',
      'use-olympus-account':   '1',
      web_tab_id:               WEB_TAB_ID,
    });
    return `https://www.doubao.com/${path}?${params.toString()}`;
  };

  // 通用 API 请求封装
  const apiFetch = async (path, bodyObj) => {
    const url  = buildUrl(path);
    const body = JSON.stringify(bodyObj);
    console.log(`→ POST ${path}  cmd=${bodyObj.cmd}`);
    const res  = await fetch(url, {
      method:      'POST',
      credentials: 'include',
      headers: {
        'content-type':             'application/json; encoding=utf-8',
        'accept':                   'application/json, text/plain, */*',
        'agw-js-conv':             'str',
        'sec-fetch-site':          'same-origin',
        'sec-fetch-mode':          'cors',
        'sec-fetch-dest':          'empty',
        'referer':                  location.href,
      },
      body,
    });
    const text = await res.text();
    console.log(`← ${path}  HTTP ${res.status}，响应: ${text.slice(0, 300)}`);
    try { return JSON.parse(text); }
    catch { throw new Error(`接口返回非 JSON: ${text.slice(0, 200)}`); }
  };

  const seqId = () => crypto.randomUUID();

  // 自动点击确认弹窗
  const setupAutoConfirm = () => {
    const CONFIRM_TEXTS = ['删除', '确认', '确定', 'Confirm', 'OK', 'Yes'];
    const observer = new MutationObserver(() => {
      document.querySelectorAll('button, [role="button"]').forEach(btn => {
        const txt = btn.innerText?.trim();
        if (txt && CONFIRM_TEXTS.includes(txt)) {
          console.log(`☑️ 自动点击: "${txt}"`);
          btn.click();
        }
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return observer;
  };
  const confirmObserver = setupAutoConfirm();

  // 从 DOM 提取未删除的消息 ID
  const getMessageIdsFromDOM = (deleted) => {
    const ids = [];
    document.querySelectorAll('[data-message-id]').forEach(el => {
      const id = el.getAttribute('data-message-id');
      if (id && !deleted.has(id)) {
        ids.push(id);
      }
    });
    return ids;
  };

  // 滚动到顶部触发加载更多消息
  const scrollAndWait = async () => {
    const candidates = [
      ...document.querySelectorAll(
        '[class*="chat"], [class*="message-list"], [class*="scroll"], [class*="conversation"]'
      ),
      document.querySelector('main'),
      document.querySelector('[role="main"]'),
      document.body,
    ];
    const scrollable = candidates.find(
      el => el && (typeof el.scrollTo === 'function' || 'scrollTop' in el)
    ) || document.body;

    if (typeof scrollable.scrollTo === 'function') {
      scrollable.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      scrollable.scrollTop = 0;
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    await new Promise(r => setTimeout(r, CONFIG.scrollDelay));
  };

  // 批量删除
  const deleteBatch = async (ids, deleted) => {
    if (ids.length === 0) return;
    const body = {
      cmd: 2210,
      uplink_body: {
        batch_update_msg_status_uplink_body: {
          conversation_id:  convId,
          conversation_type: 3,
          message_body_list: ids.map(id => ({
            message_id:       id,
            status:           5,
            local_message_id: '',
            ext:              {},
          })),
        },
      },
      sequence_id: seqId(),
      channel:     2,
      version:     '1',
    };
    try {
      const data = await apiFetch('im/message/batch_update_status', body);
      if (data?.status_code === 0) {
        ids.forEach(id => deleted.add(id));
        console.log(`✅ 已删除 ${ids.length} 条（累计 ${deleted.size} 条）`);
      } else {
        console.warn(`⚠️ 删除返回异常:`, data);
      }
    } catch (e) {
      console.error(`❌ 删除失败:`, e.message);
    }
  };

  // ========== 主流程：边滚动边删除 ==========
  console.log('%c🚀 开始批量删除...', 'color:#2196F3;font-weight:bold');
  const deleted    = new Set();   // 已删除去重
  let   noNewCount = 0;         // 连续无新消息的轮数
  let   retryDelay = CONFIG.retryBaseDelay;

  for (let round = 0; ; round++) {
    // 1. 滚动加载
    await scrollAndWait();

    // 2. 提取当前可见的未删除消息 ID
    const ids = getMessageIdsFromDOM(deleted);
    console.log(`第 ${round + 1} 轮: 发现 ${ids.length} 条未删除消息（连续无新消息: ${noNewCount} 轮）`);

    // 3. 如果有新消息，重置计数和延迟
    if (ids.length > 0) {
      noNewCount = 0;
      retryDelay = CONFIG.retryBaseDelay;
    } else {
      noNewCount++;
      if (noNewCount <= 3) {
        console.log(`⏳ 暂未加载到新消息，${1000}ms 后重试...（${noNewCount}/3）`);
        await new Promise(r => setTimeout(r, 1000));
        continue;
      }
      // 3 次之后：指数退避
      if (noNewCount < CONFIG.maxNoNewRounds) {
        console.log(`⏳ 指数退避中，等待 ${retryDelay}ms 后重试...（${noNewCount}/${CONFIG.maxNoNewRounds}）`);
        await new Promise(r => setTimeout(r, retryDelay));
        retryDelay = Math.min(retryDelay * 2, CONFIG.retryMaxDelay);
        continue;
      }
      // 达到最大重试次数，确认没有更多消息
      console.log('%c✅ 已连续 ' + CONFIG.maxNoNewRounds + ' 轮无新消息，判断加载完毕', 'color:#4CAF50;font-weight:bold');
      break;
    }

    // 4. 分批删除
    for (let i = 0; i < ids.length; i += CONFIG.batchSize) {
      const batch = ids.slice(i, i + CONFIG.batchSize);
      await deleteBatch(batch, deleted);
      await new Promise(r => setTimeout(r, CONFIG.batchDelay));
    }

    // 5. 等 DOM 更新后再继续
    await new Promise(r => setTimeout(r, 1000));
  }

  confirmObserver.disconnect();
  console.log(
    `%c🎉 全部完成！共删除 ${deleted.size} 条消息`,
    'color:#4CAF50;font-size:14px;font-weight:bold'
  );
})();
