/* V2.1 progressive enhancements. No secrets, external trackers or mocked stats. */
(() => {
  'use strict';
  const button = document.getElementById('share-profile');
  const toast = document.getElementById('toast');
  let hideTimer;
  const showToast = message => {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => toast.classList.remove('show'), 2400);
  };
  button?.addEventListener('click', async () => {
    const link = new URL(location.href);
    link.hash = 'overview';
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(link.href);
      } else {
        const input = document.createElement('textarea');
        input.value = link.href;
        input.style.cssText = 'position:fixed;left:-9999px;top:0';
        document.body.appendChild(input);
        input.select();
        if (!document.execCommand('copy')) throw new Error('clipboard unavailable');
        input.remove();
      }
      showToast('分析链接已复制，可以分享给朋友');
    } catch {
      showToast('复制失败，请从浏览器地址栏复制链接');
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.getElementById('sidebar')?.classList.contains('open')) {
      document.getElementById('sidebar-overlay')?.click();
    }
    // Keyboard users can read a given day's activity count via focus + title.
    if ((event.key === 'Enter' || event.key === ' ') && event.target?.classList?.contains('bar-item')) {
      event.preventDefault();
      showToast(event.target.getAttribute('aria-label') || '公开活动');
    }
  });
})();