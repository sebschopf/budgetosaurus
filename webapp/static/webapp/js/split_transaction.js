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
     * Initialise les dropdowns de catégorie et sous-catégorie pour une ligne de division donnée.
     * Gère le chargement des sous-catégories et la sélection initiale si un initialSubcategoryId est fourni.
     * @param {HTMLElement} splitLineElement L'élément DOM de la ligne de division.
     */
    function initializeSplitCategoryDropdowns(splitLineElement) {
        // Utilise le préfixe du formset pour trouver les éléments
        const prefix = splitLineElement.querySelector('input[name$="-description"]').name.split('-')[0]; // Ex: split_lines
        const mainCategorySelect = splitLineElement.querySelector(`select[name="${prefix}-main_category"]`);
        const subCategorySelect = splitLineElement.querySelector(`select[name="${prefix}-subcategory"]`);
        
        // Récupérer l'initial value directement du select
        const initialSubcategoryId = subCategorySelect ? subCategorySelect.value : null;

        if (mainCategorySelect && subCategorySelect) {
            // Charger les sous-catégories si une catégorie principale est déjà sélectionnée
            if (mainCategorySelect.value) {
                populateSubcategories(mainCategorySelect.value, subCategorySelect, initialSubcategoryId);
            } else {
                // Cacher le select de sous-catégorie si aucune catégorie principale n'est sélectionnée
                subCategorySelect.classList.add('subcategory-hidden');
            }

            // Écouteur pour le changement de catégorie principale
            mainCategorySelect.addEventListener('change', function() {
                populateSubcategories(this.value, subCategorySelect);
            });
        }
    }

    /**
     * Peuple le dropdown des sous-catégories en fonction de la catégorie parente sélectionnée.
     * @param {string} parentCategoryId L'ID de la catégorie parente.
     * @param {HTMLElement} subcategorySelectElement L'élément <select> des sous-catégories.
     * @param {string|null} initialSubcategoryId L'ID de la sous-catégorie à pré-sélectionner.
     */
    function populateSubcategories(parentCategoryId, subcategorySelectElement, initialSubcategoryId = null) {
        subcategorySelectElement.innerHTML = '<option value="">Sélectionner Sous-catégorie</option>';
        const childrenOfParent = allSubcategories.filter(cat => cat.parent === parseInt(parentCategoryId));

        if (childrenOfParent.length > 0) {
            childrenOfParent.forEach(subcategory => {
                const option = document.createElement('option');
                option.value = subcategory.id;
                option.textContent = subcategory.name;
                subcategorySelectElement.appendChild(option);
            });
            subcategorySelectElement.classList.remove('subcategory-hidden'); // Afficher le champ
        } else {
            subcategorySelectElement.classList.add('subcategory-hidden'); // Cacher le champ
        }

        // Sélectionner la sous-catégorie initiale si elle existe
        if (initialSubcategoryId) {
            // S'assurer que l'option existe avant de tenter de la sélectionner
            const optionExists = Array.from(subcategorySelectElement.options).some(option => option.value == initialSubcategoryId);
            if (optionExists) {
                subcategorySelectElement.value = initialSubcategoryId;
            }
        }
    }


    /**
     * Crée et ajoute une nouvelle ligne de division au formulaire (compatible formset).
     */
    function createSplitLine() {
        const currentTotalForms = parseInt(totalFormsInput.value);
        const newFormIndex = currentTotalForms;

        const div = document.createElement('div');
        div.classList.add('split-line');
        div.setAttribute('id', `form-${newFormIndex}`); // Important pour le JS de formset

        const formPrefix = 'split_lines'; // Doit correspondre au préfixe dans la vue Python
        div.innerHTML = `
            <input type="hidden" name="${formPrefix}-${newFormIndex}-id" id="id_${formPrefix}-${newFormIndex}-id">
            <input type="text" name="${formPrefix}-${newFormIndex}-description" id="id_${formPrefix}-${newFormIndex}-description" placeholder="Description" required>
            <input type="number" name="${formPrefix}-${newFormIndex}-amount" id="id_${formPrefix}-${newFormIndex}-amount" step="0.01" placeholder="Montant" required>
            <div>
                <select name="${formPrefix}-${newFormIndex}-main_category" id="id_${formPrefix}-${newFormIndex}-main_category" class="split-category-main" required>
                    <option value="">Sélectionner Catégorie Principale</option>
                    ${allCategories.map(cat => `<option value="${cat.id}">${cat.name}</option>`).join('')}
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
        totalFormsInput.value = newFormIndex + 1; // Mettre à jour TOTAL_FORMS

        addSplitLineEventListeners(div); // Attacher les événements à la nouvelle ligne
        initializeSplitCategoryDropdowns(div); // Initialiser les dropdowns de la nouvelle ligne
        calculateRemainingAmount(); // Recalculer après ajout
    }

    /**
     * Attache les écouteurs d'événements nécessaires à une ligne de division.
     * @param {HTMLElement} lineElement L'élément DOM de la ligne de division.
     */
    function addSplitLineEventListeners(lineElement) {
        const amountInput = lineElement.querySelector('input[name$="-amount"]'); // Sélectionne par la fin du nom
        const deleteBtn = lineElement.querySelector('.delete-split-btn');
        const mainCategorySelect = lineElement.querySelector('select[name$="-main_category"]');
        const subCategorySelect = lineElement.querySelector('select[name$="-subcategory"]');
        const deleteCheckbox = lineElement.querySelector('input[name$="-DELETE"]');

        if (amountInput) {
            amountInput.addEventListener('input', calculateRemainingAmount);
        }

        if (deleteBtn && deleteCheckbox) {
            deleteBtn.addEventListener('click', function() {
                // Cacher la ligne visuellement et cocher la case DELETE
                lineElement.style.display = 'none';
                deleteCheckbox.checked = true;
                calculateRemainingAmount(); // Recalculer, car cette ligne ne compte plus
            });
        }
        
        if (mainCategorySelect && subCategorySelect) {
            mainCategorySelect.addEventListener('change', function() {
                populateSubcategories(this.value, subCategorySelect);
            });
        }
    }

    /**
     * Calcule le montant restant à diviser et met à jour l'affichage du résumé.
     */
    function calculateRemainingAmount() {
        let currentSplitSum = 0;
        // Sélectionne tous les inputs de montant POUR LES LIGNES NON MARQUÉES POUR SUPPRESSION
        const splitAmountInputs = document.querySelectorAll('.split-line:not([style*="display: none"]) input[name$="-amount"]');
        splitAmountInputs.forEach(input => {
            let value = parseFloat(input.value.replace(',', '.')) || 0;
            currentSplitSum += Math.abs(value);
        });

        let remaining = originalTransactionAmount - currentSplitSum;
        remainingAmountSpan.textContent = remaining.toFixed(2);
        splitSummaryBox.classList.remove('balanced'); // Réinitialiser la classe balanced
        
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

    // --- Initialisation au chargement de la page ---
    // Attacher les événements aux lignes de formset existantes (y compris celles pré-remplies par Django)
    document.querySelectorAll('.split-line').forEach(line => {
        addSplitLineEventListeners(line);
        initializeSplitCategoryDropdowns(line);
    });

    if (addSplitLineBtn) {
        addSplitLineBtn.addEventListener('click', createSplitLine);
    }

    calculateRemainingAmount(); // Calcul initial

    // Gérer la soumission du formulaire de division
    if (splitTransactionForm) {
        splitTransactionForm.addEventListener('submit', function(event) {
            // Validation client finale, en se basant sur le calcul du montant restant
            let currentRemaining = parseFloat(remainingAmountSpan.textContent);
            if (Math.abs(currentRemaining) > 0.01) {
                event.preventDefault(); 
                alert("Attention: La somme des montants divisés ne correspond pas au montant original. Veuillez ajuster avant de soumettre.");
                return; 
            }

            // Validation client : S'assurer que chaque ligne non supprimée a une description, un montant et une catégorie valide
            const splitLines = splitLinesContainer.querySelectorAll('.split-line:not([style*="display: none"])');
            let allLinesValid = true;
            if (splitLines.length === 0) { // Ne pas permettre de soumettre sans aucune ligne non supprimée
                allLinesValid = false;
            }

            splitLines.forEach(line => {
                const descriptionInput = line.querySelector('input[name$="-description"]');
                const amountInput = line.querySelector('input[name$="-amount"]');
                const mainCategorySelect = line.querySelector('select[name$="-main_category"]');
                const subCategorySelect = line.querySelector('select[name$="-subcategory"]');

                line.classList.remove('has-error'); // Réinitialiser l'état d'erreur visuel

                if (!descriptionInput.value.trim() || !amountInput.value.trim()) {
                    allLinesValid = false;
                    line.classList.add('has-error');
                }

                let finalCategorySelected = false;
                if (subCategorySelect.value) { // Une sous-catégorie est choisie
                    const selectedSub = allSubcategories.find(s => s.id === parseInt(subCategorySelect.value));
                    if (selectedSub && selectedSub.parent === parseInt(mainCategorySelect.value)) {
                        finalCategorySelected = true;
                    }
                } else if (mainCategorySelect.value) { // Seule la catégorie principale est choisie
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
            // Le reste de la validation est géré côté serveur par le formset.
        });
    }
});
