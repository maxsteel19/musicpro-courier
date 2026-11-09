/* Tooltip de los gráficos.
   Cualquier elemento con data-tip-valor / data-tip-etiqueta muestra su dato al
   pasar el mouse o al recibir el foco con el teclado. El texto se inserta con
   textContent (nunca innerHTML), porque los nombres vienen de la base de datos. */
(function () {
    const marcas = document.querySelectorAll('[data-tip-valor]');
    if (!marcas.length) { return; }

    const tooltip = document.createElement('div');
    tooltip.className = 'viz-tooltip';
    tooltip.setAttribute('aria-hidden', 'true');
    const valor = document.createElement('strong');
    const etiqueta = document.createElement('span');
    tooltip.append(valor, etiqueta);
    document.body.appendChild(tooltip);

    function mostrar(marca, x, y) {
        valor.textContent = marca.dataset.tipValor;
        etiqueta.textContent = marca.dataset.tipEtiqueta || '';
        tooltip.style.opacity = '1';
        const ancho = tooltip.offsetWidth;
        const alto = tooltip.offsetHeight;
        const izquierda = Math.min(Math.max(8, x - ancho / 2), window.innerWidth - ancho - 8);
        const arriba = y - alto - 12 < 8 ? y + 16 : y - alto - 12;
        tooltip.style.left = izquierda + 'px';
        tooltip.style.top = arriba + 'px';
    }

    function ocultar() { tooltip.style.opacity = '0'; }

    marcas.forEach(function (marca) {
        marca.addEventListener('pointermove', function (e) { mostrar(marca, e.clientX, e.clientY); });
        marca.addEventListener('pointerleave', ocultar);
        marca.addEventListener('focus', function () {
            const r = marca.getBoundingClientRect();
            mostrar(marca, r.left + r.width / 2, r.top);
        });
        marca.addEventListener('blur', ocultar);
    });
})();
