/**
 * TG Downloader Manager — Shared JavaScript
 */

// Update refresh hint
document.addEventListener('DOMContentLoaded', () => {
    const hint = document.getElementById('refreshHint');
    if (hint) {
        let count = 15;
        setInterval(() => {
            count = count <= 1 ? 15 : count - 1;
            hint.textContent = `${count}s 后自动刷新`;
        }, 1000);
    }
});
