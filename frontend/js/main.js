// ═══════════════════════════════════════
// NAVBAR — scroll + hamburger
// ═══════════════════════════════════════
const navbar    = document.getElementById('navbar');
const hamburger = document.getElementById('hamburger');
const navLinks  = document.getElementById('navLinks');

window.addEventListener('scroll', () => {
  navbar.classList.toggle('scrolled', window.scrollY > 40);
});

hamburger.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});

navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => navLinks.classList.remove('open'));
});

// Fecha mínima = hoy
const fechaInput = document.getElementById('fecha');
if (fechaInput) {
  const hoy = new Date().toISOString().split('T')[0];
  fechaInput.min = hoy;
}

// ═══════════════════════════════════════
// UTILIDADES DE VALIDACIÓN
// ═══════════════════════════════════════
function mostrarError(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg;
}
function limpiarError(id) {
  const el = document.getElementById(id);
  if (el) el.textContent = '';
}
function marcarError(campo) {
  campo.classList.add('error');
  campo.addEventListener('input', () => campo.classList.remove('error'), { once: true });
}
function soloLetras(str) { return /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/.test(str.trim()); }
function validarEmail(email) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email); }
function validarTelefono(tel) { return /^[0-9]{7,10}$/.test(tel.trim()); }

// ═══════════════════════════════════════
// FORMULARIO DE RESERVAS
// ═══════════════════════════════════════
const reservasForm = document.getElementById('reservasForm');
const formSuccess  = document.getElementById('formSuccess');
const successMsg   = document.getElementById('successMsg');

if (reservasForm) {
  reservasForm.addEventListener('submit', function (e) {
    e.preventDefault();
    let valido = true;

    const nombre   = document.getElementById('nombre');
    const telefono = document.getElementById('telefono');
    const barbero  = document.getElementById('barbero');
    const servicio = document.getElementById('servicio');
    const fecha    = document.getElementById('fecha');
    const hora     = document.getElementById('hora');

    // Limpiar errores anteriores
    ['err-nombre','err-telefono','err-barbero','err-servicio','err-fecha','err-hora']
      .forEach(limpiarError);

    // Validar nombre
    if (!nombre.value.trim()) {
      mostrarError('err-nombre', 'El nombre es obligatorio.');
      marcarError(nombre); valido = false;
    } else if (!soloLetras(nombre.value)) {
      mostrarError('err-nombre', 'El nombre solo debe contener letras.');
      marcarError(nombre); valido = false;
    }

    // Validar teléfono
    if (!telefono.value.trim()) {
      mostrarError('err-telefono', 'El teléfono es obligatorio.');
      marcarError(telefono); valido = false;
    } else if (!validarTelefono(telefono.value)) {
      mostrarError('err-telefono', 'Ingresa un número válido (7-10 dígitos).');
      marcarError(telefono); valido = false;
    }

    // Validar barbero
    if (!barbero.value) {
      mostrarError('err-barbero', 'Selecciona un barbero.');
      marcarError(barbero); valido = false;
    }

    // Validar servicio
    if (!servicio.value) {
      mostrarError('err-servicio', 'Selecciona un servicio.');
      marcarError(servicio); valido = false;
    }

    // Validar fecha
    if (!fecha.value) {
      mostrarError('err-fecha', 'Selecciona una fecha.');
      marcarError(fecha); valido = false;
    } else {
      const hoy       = new Date(); hoy.setHours(0,0,0,0);
      const seleccion = new Date(fecha.value + 'T00:00:00');
      if (seleccion < hoy) {
        mostrarError('err-fecha', 'La fecha no puede ser en el pasado.');
        marcarError(fecha); valido = false;
      }
    }

    // Validar hora
    if (!hora.value) {
      mostrarError('err-hora', 'Selecciona una hora.');
      marcarError(hora); valido = false;
    }

    if (!valido) return;

    // Armar nombre barbero legible
    const nombresBarbero = {
      miguel: 'Miguel Ángel', carlos: 'Carlos Ruiz', luis: 'Luis Peña'
    };
    const nombresServicio = {
      corte: 'Corte clásico', fade: 'Corte + Fade',
      barba: 'Arreglo de barba', completo: 'Corte + Barba'
    };

    const fechaStr = new Date(fecha.value + 'T00:00:00')
      .toLocaleDateString('es-CO', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    successMsg.textContent =
      `${nombre.value.trim()}, tu cita con ${nombresBarbero[barbero.value]} `+
      `para ${nombresServicio[servicio.value]} está confirmada el ${fechaStr} a las ${hora.value}.`;

    reservasForm.style.display  = 'none';
    formSuccess.classList.add('show');

    // Enviar datos al backend Flask
    fetch('/api/reservar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nombre: nombre.value.trim(),
        telefono: telefono.value.trim(),
        barbero: barbero.value,
        servicio: servicio.value,
        fecha: fecha.value,
        hora: hora.value
      })
    }).catch(() => {
      // Si Flask no está activo (demo estática), no interrumpe la UX
      console.log('Modo demo: reserva simulada localmente.');
    });
  });
}

function resetForm() {
  reservasForm.reset();
  reservasForm.style.display = '';
  formSuccess.classList.remove('show');
}

// ═══════════════════════════════════════
// FORMULARIO DE CONTACTO
// ═══════════════════════════════════════
const contactoForm    = document.getElementById('contactoForm');
const contactSuccess  = document.getElementById('contactSuccess');

if (contactoForm) {
  contactoForm.addEventListener('submit', function (e) {
    e.preventDefault();
    let valido = true;

    const cNombre  = document.getElementById('c-nombre');
    const cEmail   = document.getElementById('c-email');
    const cAsunto  = document.getElementById('c-asunto');
    const cMensaje = document.getElementById('c-mensaje');

    ['err-c-nombre','err-c-email','err-c-asunto','err-c-mensaje'].forEach(limpiarError);

    if (!cNombre.value.trim()) {
      mostrarError('err-c-nombre', 'El nombre es obligatorio.');
      marcarError(cNombre); valido = false;
    } else if (!soloLetras(cNombre.value)) {
      mostrarError('err-c-nombre', 'Solo se permiten letras en el nombre.');
      marcarError(cNombre); valido = false;
    }

    if (!cEmail.value.trim()) {
      mostrarError('err-c-email', 'El correo es obligatorio.');
      marcarError(cEmail); valido = false;
    } else if (!validarEmail(cEmail.value)) {
      mostrarError('err-c-email', 'Ingresa un correo válido.');
      marcarError(cEmail); valido = false;
    }

    if (!cAsunto.value) {
      mostrarError('err-c-asunto', 'Selecciona un asunto.');
      marcarError(cAsunto); valido = false;
    }

    if (!cMensaje.value.trim() || cMensaje.value.trim().length < 10) {
      mostrarError('err-c-mensaje', 'El mensaje debe tener al menos 10 caracteres.');
      marcarError(cMensaje); valido = false;
    }

    if (!valido) return;

    contactoForm.querySelector('button[type="submit"]').disabled = true;
    contactSuccess.classList.add('show');
    contactoForm.reset();

    setTimeout(() => {
      contactSuccess.classList.remove('show');
      contactoForm.querySelector('button[type="submit"]').disabled = false;
    }, 5000);
  });
}
