// webapp/static/webapp/js/split_transaction.js

document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si la transaction originale existe avant d'initialiser le JS
    const originalTransactionInfoElement = document.querySelector('.original-transaction-info');
    if (!originalTransactionInfoElement) {
        console.log("No original transaction to split. Skipping split transaction JS initialization.");
        return; 
    }

    const originalTransactionAmount = parseFloat(document.getElementById('originalTransactionAmountData').textContent);

    const splitLinesContainer = document.getElementById('split-lines-container');
    const addSplitLineBtn = document.getElementById('add-split-line-btn');
    const splitSummaryBox = document.getElementById('split-summary-box');
    const remainingAmountSpan = document.getElementById('remaining-amount');
    const splitTransactionForm = document.getElementById('splitTransactionForm');

    // Récupérer toutes les catégories et sous-catégories en parsant le JSON du DOM
    const allCategories = JSON.parse(document.getElementById('allCategoriesData').textContent);
    const allSubcategories = JSON.parse(document.getElementById('allSubcategoriesData').textContent);
    
    // Gérer le compteur total de formulaires et le nombre de formulaires initiaux pour le formset
    const totalFormsInput = document.querySelector('#id_split_lines-TOTAL_FORMS');
    const initialFormsInput = document.querySelector('#id_split_lines-INITIAL_FORMS');
    const maxNumFormsInput = document.querySelector('#id_split_lines-MAX_NUM_FORMS'); // Nécessaire pour formset

    /**
     *Ajouter un badge d'icône à la catégorie principale ou sous-catégorie.
     * @param {string} categoryName Le nom de la catégorie.
     * @param {boolean} isFundManaged Indique si la catégorie est gérée par un fonds.
     * @returns {string} L'HTML formaté de la catégorie avec l'icône.
     */
    function formatCategoryNameWithIcon(categoryName, isFundManaged) {
        let iconClass = 'no-special'; // Default
        let iconText = 'Autre'; // Default text pour l'icône

        if (isFundManaged) {
            iconClass = 'fund-managed';
            iconText = 'Fonds';
        } 
        return `${categoryName} <span class="category-info-icon ${iconClass}">${iconText}</span>`;
    }

    /**
     * La fonction pour remplir les catégories principales dans le sélecteur.
     * @param {HTMLElement} selectElement The <select> élément pour les catégories principales.
     * @param {Array} categoriesData Données des catégories principales à afficher.
     * @param {string|number|null} initialValue Valeur initiale à pré-sélectionner, si disponible.
     */
    function populateMainCategories(selectElement, categoriesData, initialValue = null) {
        selectElement.innerHTML = '<option value="">Sélectionner Catégorie Principale</option>';
        categoriesData.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.innerHTML = formatCategoryNameWithIcon(category.name, category.is_fund_managed);
            option.dataset.isFundManaged = category.is_fund_managed; // ajouter pour l'icône si nécessaire
            selectElement.appendChild(option);
        });
        if (initialValue) {
            selectElement.value = initialValue;
        }
        // Déclencher l'événement 'change' pour mettre à jour les sous-catégories et l'icône
        selectElement.dispatchEvent(new Event('change'));
    }

    /**
     * Pour remplir les sous-catégories basées sur la catégorie principale sélectionnée.
     * @param {string} parentCategoryId ID de la catégorie principale sélectionnée.
     * @param {HTMLElement} subcategorySelectElement Le <select> élément pour les sous-catégories.
     * @param {string|null} initialSubcategoryId L'ID de la sous-catégorie initiale à pré-sélectionner, si disponible.
     */
    function populateSubcategories(parentCategoryId, subcategorySelectElement, initialSubcategoryId = null) {
        subcategorySelectElement.innerHTML = '<option value="">Sélectionner Sous-catégorie</option>';
        const childrenOfParent = allSubcategories.filter(cat => cat.parent === parseInt(parentCategoryId));

        if (childrenOfParent.length > 0) {
            childrenOfParent.forEach(subcategory => {
                const option = document.createElement('option');
                option.value = subcategory.id;
                option.innerHTML = formatCategoryNameWithIcon(subcategory.name, subcategory.is_fund_managed);
                option.dataset.isFundManaged = subcategory.is_fund_managed;
                subcategorySelectElement.appendChild(option);
            });
            subcategorySelectElement.classList.remove('subcategory-hidden'); // montrer le champ
        } else {
            subcategorySelectElement.classList.add('subcategory-hidden'); // cacher le champ s'il n'y a pas de sous-catégories
        }

        if (initialSubcategoryId) {
            // S'assurer que la sous-catégorie initiale existe avant de la sélectionner
            const optionExists = Array.from(subcategorySelectElement.options).some(option => option.value == initialSubcategoryId);
            if (optionExists) {
                subcategorySelectElement.value = initialSubcategoryId;
            }
        }
        updateCategoryIconDisplay(subcategorySelectElement); // Mettre à jour l'icône pour la sous-catégorie
    }

    /**
     * Ajoute ou met à jour l'icône d'information de la catégorie à côté du sélecteur.
     * @param {HTMLElement} selectElement élément <select> pour lequel mettre à jour l'icône.
     */
    function updateCategoryIconDisplay(selectElement) {
        let currentIcon = selectElement.nextElementSibling;
        if (currentIcon && currentIcon.classList.contains('category-info-icon')) {
            currentIcon.remove();
        }

        const selectedOption = selectElement.options[selectElement.selectedIndex];
        if (selectedOption && selectedOption.value) { // Ajouter seulement si une option est sélectionnée
            const isFundManaged = selectedOption.dataset.isFundManaged === 'true'; // 'true' est la valeur attendue pour un fonds géré
            
            const iconSpan = document.createElement('span');
            iconSpan.innerHTML = formatCategoryNameWithIcon('', isFundManaged); // Formatage de l'icône sans texte initial
            iconSpan.classList.add('category-info-icon'); // basique class pour le style
            iconSpan.classList.add(isFundManaged ? 'fund-managed' : 'no-special');
            iconSpan.textContent = isFundManaged ? 'Fonds' : 'Autre'; // texte par défaut

            // Insérer l'icône après le sélecteur
            selectElement.parentNode.insertBefore(iconSpan, selectElement.nextSibling);
        }
    }


    /**
     * Créer et ajoute une nouvelle ligne de division au formulaire.
     */
    function createSplitLine() {
        const currentTotalForms = parseInt(totalFormsInput.value);
        const newFormIndex = currentTotalForms;

        const div = document.createElement('div');
        div.classList.add('split-line');
        div.setAttribute('id', `form-${newFormIndex}`); // Important pour le formset Django

        const formPrefix = 'split_lines'; // Doit être le même que le préfixe utilisé dans le formset Django !
        div.innerHTML = `
            <input type="hidden" name="${formPrefix}-${newFormIndex}-id" id="id_${formPrefix}-${newFormIndex}-id">
            <input type="text" name="${formPrefix}-${newFormIndex}-description" id="id_${formPrefix}-${newFormIndex}-description" placeholder="Description" required>
            <input type="number" name="${formPrefix}-${newFormIndex}-amount" id="id_${formPrefix}-${newFormIndex}-amount" step="0.01" placeholder="Montant" required>
            <div>
                <select name="${formPrefix}-${newFormIndex}-main_category" id="id_${formPrefix}-${newFormIndex}-main_category" class="split-category-main" required>
                    <option value="">Sélectionner Catégorie Principale</option>
                    ${allCategories.map(cat => `<option value="${cat.id}">${cat.html}</option>`).join('')}
                </select>
                <select name="${formPrefix}-${newFormIndex}-subcategory" id="id_${formPrefix}-${newFormIndex}-subcategory" class="split-category subcategory-hidden">
                    <option value="">Sélectionner Sous-catégorie</option>
                </select>
            </div>
            <div class="flex items-center justify-center">
                <input type="checkbox" name="${formPrefix}-${newFormIndex}-DELETE" id="id_${formPrefix}-${newFormIndex}-DELETE" class="hidden-delete-checkbox">
                <label for="id_${formPrefix}-${newFormIndex}-DELETE" class="sr-only">Supprimer</label>
                <button type="button" class="delete-split-btn">X</button>
            </div>
        `;
        
        splitLinesContainer.appendChild(div);
        totalFormsInput.value = newFormIndex + 1; // Update TOTAL_FORMS

        addSplitLineEventListeners(div); // lier les événements à la nouvelle ligne
        initializeSplitCategoryDropdowns(div); // Initialise les sélecteurs de catégorie pour la nouvelle ligne
        calculateRemainingAmount(); // Recalculer le montant restant après l'ajout d'une nouvelle ligne
    }

    /**
     * Ajoute les écouteurs d'événements nécessaires à une ligne de division.
     * @param {HTMLElement} lineElement The DOM element de la ligne de division.
     */
    function addSplitLineEventListeners(lineElement) {
        const amountInput = lineElement.querySelector('input[name$="-amount"]'); // Selection de l'input de montant
        const deleteBtn = lineElement.querySelector('.delete-split-btn');
        const mainCategorySelect = lineElement.querySelector('select[name$="-main_category"]');
        const subCategorySelect = lineElement.querySelector('select[name$="-subcategory"]');
        const deleteCheckbox = lineElement.querySelector('input[name$="-DELETE"]');

        if (amountInput) {
            amountInput.addEventListener('input', calculateRemainingAmount);
        }

        if (deleteBtn && deleteCheckbox) {
            deleteBtn.addEventListener('click', function() {
                // Hide the line visually and check the DELETE checkbox
                lineElement.style.display = 'none';
                deleteCheckbox.checked = true;
                calculateRemainingAmount(); // Recalculate, as this line no longer counts
            });
        }
        
        if (mainCategorySelect) {
            mainCategorySelect.addEventListener('change', function() {
                populateSubcategories(this.value, subCategorySelect);
                updateCategoryIconDisplay(this); // Update icon for main category
            });
        }
        if (subCategorySelect) {
            subCategorySelect.addEventListener('change', function() {
                updateCategoryIconDisplay(this); // Update icon for subcategory
            });
        }
    }

    /**
     * Initializes category and subcategory dropdowns for a given split line.
     * Manages loading subcategories and initial selection if an initialSubcategoryId is provided.
     * @param {HTMLElement} splitLineElement The DOM element of the split line.
     */
    function initializeSplitCategoryDropdowns(splitLineElement) {
        const prefix = splitLineElement.querySelector('input[name$="-description"]').name.split('-')[0]; // Ex: split_lines
        const mainCategorySelect = splitLineElement.querySelector(`select[name="${prefix}-main_category"]`);
        const subCategorySelect = splitLineElement.querySelector(`select[name="${prefix}-subcategory"]`);
        
        // Populate main categories with icons
        const initialMainCategoryValue = mainCategorySelect.value; // Get initial value from Django form
        populateMainCategories(mainCategorySelect, allCategories, initialMainCategoryValue);

        // If there was an initial subcategory value, populateSubcategories will handle selecting it
        const initialSubcategoryId = subCategorySelect ? subCategorySelect.value : null;

        if (mainCategorySelect.value) {
            populateSubcategories(mainCategorySelect.value, subCategorySelect, initialSubcategoryId);
        } else {
            subCategorySelect.classList.add('subcategory-hidden');
            updateCategoryIconDisplay(subCategorySelect); // Clear icon if subcategory is hidden
        }
        updateCategoryIconDisplay(mainCategorySelect); // Initial display for main category
    }


    /**
     * Calculates the remaining amount to split and updates the summary display.
     */
    function calculateRemainingAmount() {
        let currentSplitSum = 0;
        // Selects all amount inputs FOR LINES NOT MARKED FOR DELETION
        const splitAmountInputs = document.querySelectorAll('.split-line:not([style*="display: none"]) input[name$="-amount"]');
        splitAmountInputs.forEach(input => {
            let value = parseFloat(input.value.replace(',', '.')) || 0;
            currentSplitSum += Math.abs(value);
        });

        let remaining = originalTransactionAmount - currentSplitSum;
        remainingAmountSpan.textContent = remaining.toFixed(2);
        splitSummaryBox.classList.remove('balanced'); // Reset balanced class
        
        if (Math.abs(remaining) < 0.01) {
            splitSummaryBox.classList.add('balanced');
        }

        remainingAmountSpan.classList.remove('positive', 'negative');
        if (remaining > 0.01) {
            remainingAmountSpan.classList.add('positive');
        } else if (remaining < -0.01) {
            remainingAmountSpan.classList.add('negative');
        }
    }

    // --- Initialization on page load ---
    // Attach events to existing formset lines (including those pre-filled by Django)
    document.querySelectorAll('.split-line').forEach(line => {
        addSplitLineEventListeners(line);
        initializeSplitCategoryDropdowns(line);
    });

    if (addSplitLineBtn) {
        addSplitLineBtn.addEventListener('click', createSplitLine);
    }

    calculateRemainingAmount(); // Initial calculation

    // Handle split form submission
    if (splitTransactionForm) {
        splitTransactionForm.addEventListener('submit', function(event) {
            // Final client-side validation, based on remaining amount calculation
            let currentRemaining = parseFloat(remainingAmountSpan.textContent);
            if (Math.abs(currentRemaining) > 0.01) {
                event.preventDefault(); 
                alert("Attention: La somme des montants divisés ne correspond pas au montant original. Veuillez ajuster avant de soumettre.");
                return; 
            }

            // Client-side validation: Ensure each non-deleted line has a description, amount, and valid category
            const splitLines = splitLinesContainer.querySelectorAll('.split-line:not([style*="display: none"])');
            let allLinesValid = true;
            if (splitLines.length === 0) { // Do not allow submitting without any non-deleted lines
                allLinesValid = false;
            }

            splitLines.forEach(line => {
                const descriptionInput = line.querySelector('input[name$="-description"]');
                const amountInput = line.querySelector('input[name$="-amount"]');
                const mainCategorySelect = line.querySelector('select[name$="-main_category"]');
                const subCategorySelect = line.querySelector('select[name$="-subcategory"]');

                line.classList.remove('has-error'); // Reset visual error state

                if (!descriptionInput.value.trim() || !amountInput.value.trim()) {
                    allLinesValid = false;
                    line.classList.add('has-error');
                }

                let finalCategorySelected = false;
                if (subCategorySelect.value) { // A subcategory is chosen
                    const selectedSub = allSubcategories.find(s => s.id === parseInt(subCategorySelect.value));
                    if (selectedSub && selectedSub.parent === parseInt(mainCategorySelect.value)) {
                        finalCategorySelected = true;
                    }
                } else if (mainCategorySelect.value) { // Only the main category is chosen
                        finalCategorySelected = true;
                }
                
                if (!finalCategorySelected) {
                    allLinesValid = false;
                    line.classList.add('has-error');
                }
            });

            if (!allLinesValid) {
                event.preventDefault(); 
                alert("Veuillez remplir toutes les informations requises (description, montant, catégorie) pour chaque ligne de division, et vérifier la cohérence des catégories.");
            }
            // The rest of the validation is handled server-side by the formset.
        });
    }
});
