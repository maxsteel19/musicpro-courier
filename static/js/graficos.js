/* Gráficos del panel y de los reportes (Chart.js). Los datos vienen del ORM
   a través de {{ datos|json_script }} para evitar inyección de HTML. */
(function () {
    const COLORES = ['#58a6ff', '#3fb950', '#e3b341', '#f85149', '#a371f7', '#f0883e', '#39c5cf', '#e63946'];
    if (window.Chart) {
        Chart.defaults.color = '#8b949e';
        Chart.defaults.borderColor = '#30363d';
        Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";
    }

    window.leerDatos = function (id) {
        const nodo = document.getElementById(id);
        return nodo ? JSON.parse(nodo.textContent) : { etiquetas: [], valores: [] };
    };

    function crear(id, config) {
        const lienzo = document.getElementById(id);
        if (lienzo && window.Chart) { return new Chart(lienzo, config); }
        return null;
    }

    window.graficoDona = function (id, datos) {
        return crear(id, {
            type: 'doughnut',
            data: { labels: datos.etiquetas, datasets: [{ data: datos.valores, backgroundColor: COLORES, borderWidth: 0 }] },
            options: { plugins: { legend: { position: 'bottom' } }, cutout: '62%' }
        });
    };

    window.graficoBarras = function (id, datos) {
        return crear(id, {
            type: 'bar',
            data: { labels: datos.etiquetas, datasets: [{ label: 'Viajes', data: datos.valores, backgroundColor: COLORES, borderRadius: 6 }] },
            options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
        });
    };

    window.graficoLinea = function (id, datos) {
        return crear(id, {
            type: 'line',
            data: { labels: datos.etiquetas, datasets: [{ label: 'Viajes', data: datos.valores, borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,.15)', fill: true, tension: .35 }] },
            options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } }
        });
    };
})();
