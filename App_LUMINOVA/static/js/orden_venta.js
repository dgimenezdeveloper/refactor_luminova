// Script para mejorar la experiencia de usuario en la creación de Órdenes de Venta
// Maneja la selección de productos y muestra información de stock en tiempo real

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar eventos para productos existentes
    initializeProductSelectEvents();
    
    // Configurar evento para nuevos productos añadidos dinámicamente
    const addItemButton = document.getElementById('add-item-button');
    if (addItemButton) {
        addItemButton.addEventListener('click', function() {
            // Esperar un poco para que el nuevo formulario se agregue al DOM
            setTimeout(() => {
                initializeProductSelectEvents();
            }, 100);
        });
    }
});

function initializeProductSelectEvents() {
    // Buscar todos los selectores de producto
    const productSelectors = document.querySelectorAll('.producto-selector-ov-item');
    
    productSelectors.forEach(selector => {
        // Remover listener previo si existe
        selector.removeEventListener('change', handleProductChange);
        // Agregar nuevo listener
        selector.addEventListener('change', handleProductChange);
    });
}

function handleProductChange(event) {
    const productSelect = event.target;
    const productId = productSelect.value;
    const formRow = productSelect.closest('.item-form');
    
    if (!productId) {
        clearProductInfo(formRow);
        return;
    }
    
    // Buscar campos relacionados en el mismo formulario
    const precioField = formRow.querySelector('.precio-ov-item');
    const cantidadField = formRow.querySelector('.cantidad-ov-item');
    
    // Mostrar información de carga
    showLoadingInfo(formRow);
    
    // Realizar petición AJAX para obtener información del producto
    fetch(`/ajax/productos/get-stock-info/?producto_id=${productId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showErrorInfo(formRow, data.error);
                return;
            }
            
            // Actualizar precio unitario
            if (precioField) {
                precioField.value = data.precio_unitario;
            }
            
            // Mostrar información de stock
            showStockInfo(formRow, data);
            
            // Validar cantidad si ya está seleccionada
            if (cantidadField && cantidadField.value) {
                validateQuantity(cantidadField, data.stock_total);
            }
        })
        .catch(error => {
            console.error('Error al obtener información del producto:', error);
            showErrorInfo(formRow, 'Error al cargar información del producto');
        });
}

function showLoadingInfo(formRow) {
    removeExistingInfo(formRow);
    
    const infoDiv = document.createElement('div');
    infoDiv.className = 'stock-info alert alert-info mt-2';
    infoDiv.innerHTML = '<i class="bi bi-hourglass-split"></i> Cargando información de stock...';
    
    formRow.appendChild(infoDiv);
}

function showStockInfo(formRow, data) {
    removeExistingInfo(formRow);
    
    const infoDiv = document.createElement('div');
    infoDiv.className = 'stock-info alert alert-success mt-2';
    
    let stockHtml = `
        <strong><i class="bi bi-box-seam"></i> Stock disponible: ${data.stock_total}</strong><br>
        <small>Precio unitario: $${data.precio_unitario}</small>
    `;
    
    if (data.stock_por_deposito && data.stock_por_deposito.length > 0) {
        stockHtml += '<br><small><strong>Por depósito:</strong><br>';
        data.stock_por_deposito.forEach(deposito => {
            stockHtml += `${deposito.deposito__nombre}: ${deposito.cantidad}<br>`;
        });
        stockHtml += '</small>';
    }
    
    infoDiv.innerHTML = stockHtml;
    formRow.appendChild(infoDiv);
    
    // Configurar validación de cantidad
    const cantidadField = formRow.querySelector('.cantidad-ov-item');
    if (cantidadField) {
        cantidadField.removeEventListener('input', validateQuantityInput);
        cantidadField.addEventListener('input', function() {
            validateQuantity(this, data.stock_total);
        });
        
        // Validar cantidad actual si existe
        if (cantidadField.value) {
            validateQuantity(cantidadField, data.stock_total);
        }
    }
}

function showErrorInfo(formRow, message) {
    removeExistingInfo(formRow);
    
    const infoDiv = document.createElement('div');
    infoDiv.className = 'stock-info alert alert-danger mt-2';
    infoDiv.innerHTML = `<i class="bi bi-exclamation-triangle"></i> ${message}`;
    
    formRow.appendChild(infoDiv);
}

function clearProductInfo(formRow) {
    removeExistingInfo(formRow);
    
    // Limpiar precio
    const precioField = formRow.querySelector('.precio-ov-item');
    if (precioField) {
        precioField.value = '';
    }
}

function removeExistingInfo(formRow) {
    const existingInfo = formRow.querySelector('.stock-info');
    if (existingInfo) {
        existingInfo.remove();
    }
}

function validateQuantity(cantidadField, stockDisponible) {
    const cantidad = parseInt(cantidadField.value) || 0;
    const formRow = cantidadField.closest('.item-form');
    
    // Remover clases de validación previas
    cantidadField.classList.remove('is-valid', 'is-invalid');
    
    // Remover mensaje de validación previo
    const existingFeedback = formRow.querySelector('.quantity-validation-feedback');
    if (existingFeedback) {
        existingFeedback.remove();
    }
    
    if (cantidad > stockDisponible) {
        cantidadField.classList.add('is-invalid');
        
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'quantity-validation-feedback invalid-feedback';
        feedbackDiv.textContent = `Stock insuficiente. Disponible: ${stockDisponible}`;
        
        cantidadField.parentNode.appendChild(feedbackDiv);
        return false;
    } else if (cantidad > 0) {
        cantidadField.classList.add('is-valid');
        return true;
    }
    
    return true;
}

// Función para validar todo el formulario antes del envío
function validateFormBeforeSubmit() {
    const productSelectors = document.querySelectorAll('.producto-selector-ov-item');
    let isValid = true;
    
    productSelectors.forEach(selector => {
        const formRow = selector.closest('.item-form');
        const cantidadField = formRow.querySelector('.cantidad-ov-item');
        
        if (selector.value && cantidadField && cantidadField.value) {
            if (cantidadField.classList.contains('is-invalid')) {
                isValid = false;
            }
        }
    });
    
    return isValid;
}

// Agregar validación al envío del formulario
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('formCrearOV');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!validateFormBeforeSubmit()) {
                event.preventDefault();
                alert('Por favor, corrija los errores de stock antes de continuar.');
            }
        });
    }
});
