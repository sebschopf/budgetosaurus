// webapp/static/webapp/js/allocate_income.js

document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si l'élément de transaction originale existe avant d'initialiser le JS
    const originalTransactionInfoElement = document.querySelector('.original-transaction-info');
    if (!originalTransactionInfoElement) {
        console.log("Aucune transaction originale trouvée pour l'allocation. Initialisation JS ignorée.");
        return; 
    }

    const originalTransactionAmount = parseFloat(document.getElementById('originalTransactionAmountData').textContent);

    const allocationLinesContainer = document.getElementById('allocation-lines-container');
    const addAllocationLineBtn = document.getElementById('add-allocation-line-btn');
    const allocationSummaryBox = document.getElementById('allocation-summary-box');
    const remainingAmountSpan = document.getElementById('remaining-amount');
    const allocationForm = document.getElementById('allocationForm');

    // Récupérer les données des catégories gérées par fonds du DOM
    const fundManagedCategories = JSON.parse(document.getElementById('fundManagedCategoriesData').textContent);
    
    // Gérer le compteur total de formulaires pour le formset
    const totalFormsInput = document.querySelector('#id_form-TOTAL_FORMS'); // Note : le préfixe du formset peut être 'form' par défaut si non spécifié
    const initialFormsInput = document.querySelector('#id_form-INITIAL_FORMS');
    // const maxNumFormsInput = document.querySelector('#id_form-MAX_NUM_FORMS'); // Pas strictement nécessaire pour les fonctionnalités côté client

    /**
     * Ajoute une icône/badge à côté d'un nom de catégorie.
     * @param {string} categoryName Le nom de la catégorie.
     * @param {boolean} isFundManaged Indique si la catégorie gère un fonds.
     * @returns {string} Le HTML du nom de catégorie avec l'icône.
     */
    function formatCategoryNameWithIcon(categoryName, isFundManaged) {
        let iconClass = 'no-special'; // Par défaut
        let iconText = 'Autre'; // Texte par défaut pour la gestion non spéciale

        if (isFundManaged) {
            iconClass = 'fund-managed';
            iconText = 'Fonds';
        } 
        return `${categoryName} <span class="category-info-icon ${iconClass}">${iconText}</span>`;
    }

    /**
     * Remplit la liste déroulante des catégories pour une ligne d'allocation avec des icônes.
     * @param {HTMLElement} selectElement L'élément <select> à remplir.
     * @param {Array} categoriesData Les données des catégories gérées par fonds.
     * @param {string|number|null} initialValue La valeur initiale à sélectionner.
     */
    function populateCategoryDropdown(selectElement, categoriesData, initialValue = null) {
        selectElement.innerHTML = '<option value="">Sélectionner le Fonds (Catégorie)</option>';
        categoriesData.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.innerHTML = formatCategoryNameWithIcon(category.name, category.is_fund_managed);
            option.dataset.isFundManaged = category.is_fund_managed; // Stocker pour une utilisation ultérieure
            selectElement.appendChild(option);
        });
        if (initialValue) {
            selectElement.value = initialValue;
        }
        // Déclencher le changement pour mettre à jour l'icône affichée à côté du champ select
        selectElement.dispatchEvent(new Event('change'));
    }

    /**
     * Affiche l'icône de la catégorie sélectionnée à côté de l'élément select.
     * @param {HTMLElement} selectElement L'élément <select> de la catégorie.
     */
    function updateCategoryIconDisplay(selectElement) {
        let currentIcon = selectElement.nextElementSibling;
        if (currentIcon && currentIcon.classList.contains('category-info-icon')) {
            currentIcon.remove();
        }

        const selectedOption = selectElement.options[selectElement.selectedIndex];
        if (selectedOption && selectedOption.value) { // N'ajouter que si une catégorie réelle est sélectionnée
            const isFundManaged = selectedOption.dataset.isFundManaged === 'true'; // 'true' est une chaîne de caractères du dataset
            
            const iconSpan = document.createElement('span');
            iconSpan.innerHTML = formatCategoryNameWithIcon('', isFundManaged); // Formater uniquement la partie icône
            iconSpan.classList.add('category-info-icon'); // S'assurer de la classe de base
            iconSpan.classList.add(isFundManaged ? 'fund-managed' : 'no-special');
            iconSpan.textContent = isFundManaged ? 'Fonds' : 'Autre'; // Texte pour le badge

            // Insérer l'icône juste après l'élément select
            selectElement.parentNode.insertBefore(iconSpan, selectElement.nextSibling);
        }
    }

    /**
     * Crée et ajoute une nouvelle ligne d'allocation au formulaire (compatible formset).
     */
    function createAllocationLine() {
        const currentTotalForms = parseInt(totalFormsInput.value);
        const newFormIndex = currentTotalForms;

        const div = document.createElement('div');
        div.classList.add('allocation-line');
        div.setAttribute('id', `form-${newFormIndex}`); // Important pour le JS du formset (le préfixe par défaut est 'form')

        const formPrefix = 'form'; // Préfixe de formset par défaut dans Django, sauf spécification contraire
        div.innerHTML = `
            <input type="hidden" name="${formPrefix}-${newFormIndex}-id" id="id_${formPrefix}-${newFormIndex}-id">
            <div>
                <select name="${formPrefix}-${newFormIndex}-category" id="id_${formPrefix}-${newFormIndex}-category" required>
                    <option value="">Sélectionner le Fonds (Catégorie)</option>
                </select>
            </div>
            <input type="number" name="${formPrefix}-${newFormIndex}-amount" id="id_${formPrefix}-${newFormIndex}-amount" step="0.01" placeholder="Montant alloué" required>
            <input type="text" name="${formPrefix}-${newFormIndex}-notes" id="id_${formPrefix}-${newFormIndex}-notes" placeholder="Notes (optionnel)">
            <div class="flex items-center justify-center">
                <input type="checkbox" name="${formPrefix}-${newFormIndex}-DELETE" id="id_${formPrefix}-${newFormIndex}-DELETE" class="hidden-delete-checkbox">
                <label for="id_${formPrefix}-${newFormIndex}-DELETE" class="sr-only">Supprimer</label>
                <button type="button" class="delete-line-btn">X</button>
            </div>
        `;
        
        allocationLinesContainer.appendChild(div);
        totalFormsInput.value = newFormIndex + 1; // Mettre à jour TOTAL_FORMS

        addAllocationLineEventListeners(div); // Attacher les événements à la nouvelle ligne
        initializeAllocationCategoryDropdowns(div); // Initialiser les listes déroulantes pour la nouvelle ligne
        calculateRemainingAmount(); // Recalculer après l'ajout
    }

    /**
     * Attache les écouteurs d'événements nécessaires à une ligne d'allocation.
     * @param {HTMLElement} lineElement L'élément DOM de la ligne d'allocation.
     */
    function addAllocationLineEventListeners(lineElement) {
        const amountInput = lineElement.querySelector('input[name$="-amount"]');
        const deleteBtn = lineElement.querySelector('.delete-line-btn');
        const categorySelect = lineElement.querySelector('select[name$="-category"]');
        const deleteCheckbox = lineElement.querySelector('input[name$="-DELETE"]');

        if (amountInput) {
            amountInput.addEventListener('input', calculateRemainingAmount);
        }

        if (deleteBtn && deleteCheckbox) {
            deleteBtn.addEventListener('click', function() {
                // Masquer visuellement la ligne et cocher la case de suppression
                lineElement.style.display = 'none';
                deleteCheckbox.checked = true;
                calculateRemainingAmount(); // Recalculer, car cette ligne ne compte plus
            });
        }
        
        if (categorySelect) {
            categorySelect.addEventListener('change', function() {
                updateCategoryIconDisplay(this);
            });
        }
    }

    /**
     * Initialise les listes déroulantes de catégories pour une ligne d'allocation donnée.
     * @param {HTMLElement} allocationLineElement L'élément DOM de la ligne d'allocation.
     */
    function initializeAllocationCategoryDropdowns(allocationLineElement) {
        const prefix = allocationLineElement.querySelector('input[name$="-amount"]').name.split('-')[0];
        const categorySelect = allocationLineElement.querySelector(`select[name="${prefix}-category"]`);
        
        const initialCategoryValue = categorySelect.value; // Obtenir la valeur initiale du formulaire Django
        populateCategoryDropdown(categorySelect, fundManagedCategories, initialCategoryValue);
    }


    /**
     * Calcule le montant restant à allouer et met à jour l'affichage du résumé.
     */
    function calculateRemainingAmount() {
        let currentAllocatedSum = 0;
        // Sélectionne toutes les entrées de montant POUR LES LIGNES NON MARQUÉES POUR SUPPRESSION
        const allocatedAmountInputs = document.querySelectorAll('.allocation-line:not([style*="display: none"]) input[name$="-amount"]');
        allocatedAmountInputs.forEach(input => {
            let value = parseFloat(input.value.replace(',', '.')) || 0;
            currentAllocatedSum += value; // Les montants pour l'allocation doivent être positifs
        });

        let remaining = originalTransactionAmount - currentAllocatedSum;
        remainingAmountSpan.textContent = remaining.toFixed(2);
        allocationSummaryBox.classList.remove('balanced'); // Réinitialiser la classe balanced
        
        // Ajouter une petite tolérance pour les comparaisons en virgule flottante
        if (Math.abs(remaining) < 0.01) { 
            allocationSummaryBox.classList.add('balanced');
        }

        remainingAmountSpan.classList.remove('positive', 'negative');
        if (remaining > 0.01) {
            remainingAmountSpan.classList.add('positive');
        } else if (remaining < -0.01) {
            remainingAmountSpan.classList.add('negative');
            // Ajouter un indicateur visuel ou un avertissement si l'allocation dépasse la transaction originale
            allocationSummaryBox.classList.remove('balanced');
            allocationSummaryBox.classList.add('has-error'); // Vous pouvez vouloir une classe d'erreur spécifique pour cette boîte
        } else {
            allocationSummaryBox.classList.remove('has-error');
        }
    }

    // --- Initialisation au chargement de la page ---
    // Attacher les événements aux lignes du formset existantes (y compris celles pré-remplies par Django)
    document.querySelectorAll('.allocation-line').forEach(line => {
        addAllocationLineEventListeners(line);
        initializeAllocationCategoryDropdowns(line);
    });

    if (addAllocationLineBtn) {
        addAllocationLineBtn.addEventListener('click', createAllocationLine);
    }

    calculateRemainingAmount(); // Calcul initial

    // Gérer la soumission du formulaire d'allocation
    if (allocationForm) {
        allocationForm.addEventListener('submit', function(event) {
            // Validation finale côté client, basée sur le calcul du montant restant
            let currentRemaining = parseFloat(remainingAmountSpan.textContent);
            if (currentRemaining < -0.01) { // Vérifier si l'allocation dépasse le montant de la transaction originale
                event.preventDefault(); 
                alert("Attention : Le montant total alloué dépasse le montant de la transaction originale. Veuillez ajuster avant de soumettre.");
                return; 
            }

            // Validation côté client : S'assurer que chaque ligne non supprimée a une catégorie et un montant
            const lines = allocationLinesContainer.querySelectorAll('.allocation-line:not([style*="display: none"])');
            let allLinesValid = true;
            if (lines.length === 0) {
                allLinesValid = false;
            }

            lines.forEach(line => {
                const categorySelect = line.querySelector('select[name$="-category"]');
                const amountInput = line.querySelector('input[name$="-amount"]');

                line.classList.remove('has-error'); // Réinitialiser l'état d'erreur visuel

                if (!categorySelect.value || !amountInput.value.trim()) {
                    allLinesValid = false;
                    line.classList.add('has-error');
                }
            });

            if (!allLinesValid) {
                event.preventDefault(); 
                alert("Veuillez remplir toutes les informations requises (Fonds/Enveloppe, Montant) pour chaque ligne d'allocation.");
            }
            // Le reste de la validation est géré côté serveur par le formset.
        });
    }
});
