// webapp/static/webapp/js/split_transaction.js

document.addEventListener('DOMContentLoaded', function() {
    const originalTransactionInfoElement = document.querySelector('.original-transaction-info');
    if (!originalTransactionInfoElement) {
        console.log("No original transaction to split. Skipping split transaction JS initialization.");
        return; 
    }

    // Montant de la transaction originale (sera toujours positif pour les calculs de division)
    const originalTransactionAmount = Math.abs(parseFloat(document.getElementById('originalTransactionAmountData')?.textContent || '0'));

    const splitLinesContainer = document.getElementById('split-lines-container');
    const addSplitLineBtn = document.getElementById('add-split-line-btn');
    const splitSummaryBox = document.getElementById('split-summary-box');
    const remainingAmountSpan = document.getElementById('remaining-amount');
    const splitTransactionForm = document.getElementById('splitTransactionForm');
    const splitGuidanceText = document.getElementById('split-guidance');
    const mainSubmitBtn = document.querySelector('.main-submit-btn'); // Sélection du bouton de soumission

    // Récupérer toutes les catégories et sous-catégories en parsant le JSON du DOM
    const allCategories = JSON.parse(document.getElementById('allCategoriesData')?.textContent || '[]');
    const allSubcategories = JSON.parse(document.getElementById('allSubcategoriesData')?.textContent || '[]');
    
    const totalFormsInput = document.querySelector('#id_split_lines-TOTAL_FORMS');

    // Récupérer la description originale une fois pour toutes, de manière robuste
    const originalDescription = originalTransactionInfoElement.querySelector('p:nth-of-type(2)')?.textContent.replace('Description: ', '').trim() || '';

    /**
     * Crée un élément span pour un badge de catégorie.
     * @param {string} text Le texte du badge (ex: "Fonds", "Budget", "Objectif").
     * @param {string} className La classe CSS pour la couleur (ex: "fund-managed", "budgeted", "goal-linked").
     * @returns {HTMLElement} L'élément span du badge.
     */
    function createCategoryBadge(text, className) {
        const span = document.createElement('span');
        span.classList.add('category-info-icon', className);
        span.textContent = text;
        return span;
    }

    /**
     * La fonction pour remplir les catégories principales dans le sélecteur.
     * @param {HTMLElement} selectElement The <select> élément pour les catégories principales.
     * @param {Array} categoriesData Les données des catégories.
     * @param {string|number|null} initialValue Valeur initiale à pré-sélectionner, si disponible.
     */
    function populateMainCategories(selectElement, categoriesData, initialValue = null) {
        selectElement.innerHTML = '<option value="">Sélectionner Catégorie Principale</option>';
        categoriesData.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name; // Texte de l'option sans HTML
            option.dataset.isFundManaged = category.is_fund_managed;
            option.dataset.isBudgeted = category.is_budgeted; 
            option.dataset.isGoalLinked = category.is_goal_linked; // NOUVEAU: info is_goal_linked
            selectElement.appendChild(option);
        });
        if (initialValue) {
            selectElement.value = initialValue;
        }
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
                option.textContent = subcategory.name; // Texte de l'option sans HTML
                option.dataset.isFundManaged = subcategory.is_fund_managed;
                option.dataset.isBudgeted = subcategory.is_budgeted; 
                option.dataset.isGoalLinked = subcategory.is_goal_linked; // NOUVEAU: info is_goal_linked
                subcategorySelectElement.appendChild(option);
            });
            subcategorySelectElement.classList.remove('subcategory-hidden');
        } else {
            subcategorySelectElement.classList.add('subcategory-hidden');
        }

        if (initialSubcategoryId) {
            const optionExists = Array.from(subcategorySelectElement.options).some(option => option.value == initialSubcategoryId);
            if (optionExists) {
                subcategorySelectElement.value = initialSubcategoryId;
            }
        }
        updateCategoryIconDisplay(subcategorySelectElement);
    }

    /**
     * Ajoute ou met à jour les icônes d'information de la catégorie à côté de l'élément select.
     * Permet d'afficher plusieurs badges (Fonds, Budget, Objectif).
     * @param {HTMLElement} selectElement élément <select> pour lequel mettre à jour les icônes.
     */
    function updateCategoryIconDisplay(selectElement) {
        // Supprimer tous les badges existants associés à ce select
        let currentNextSibling = selectElement.nextElementSibling;
        while (currentNextSibling && currentNextSibling.classList.contains('category-info-icon')) {
            const temp = currentNextSibling.nextElementSibling;
            currentNextSibling.remove();
            currentNextSibling = temp;
        }

        const selectedOption = selectElement.options[selectElement.selectedIndex];
        if (selectedOption && selectedOption.value) {
            const isFundManaged = selectedOption.dataset.isFundManaged === 'true'; 
            const isBudgeted = selectedOption.dataset.isBudgeted === 'true';
            const isGoalLinked = selectedOption.dataset.isGoalLinked === 'true'; 
            
            const parentNode = selectElement.parentNode;

            // Ajouter les badges pertinents
            if (isFundManaged) {
                parentNode.insertBefore(createCategoryBadge('Fonds', 'fund-managed'), selectElement.nextSibling);
            }
            if (isBudgeted) {
                parentNode.insertBefore(createCategoryBadge('Budget', 'budgeted'), selectElement.nextSibling);
            }
            if (isGoalLinked) { 
                parentNode.insertBefore(createCategoryBadge('Objectif', 'goal-linked'), selectElement.nextSibling);
            }
            // Si aucune des conditions n'est vraie, aucun badge n'est ajouté.
        }
    }


    /**
     * Créer et ajoute une nouvelle ligne de division au formulaire.
     * @param {object} initialData Données pour pré-remplir la nouvelle ligne (optionnel).
     * @returns {HTMLElement|null} La nouvelle ligne div ou null si erreur.
     */
    function createSplitLine(initialData = {}) {
        if (!totalFormsInput) {
            console.error("Erreur: L'élément #id_split_lines-TOTAL_FORMS est introuvable. Impossible de créer de nouvelles lignes.");
            return null;
        }

        let currentTotalForms = parseInt(totalFormsInput.value);
        if (isNaN(currentTotalForms)) {
            console.error("Erreur: La valeur de totalFormsInput n'est pas un nombre valide:", totalFormsInput.value);
            totalFormsInput.value = '0'; 
            currentTotalForms = 0;
        }

        const newFormIndex = currentTotalForms;
        const formPrefix = 'split_lines'; 

        const div = document.createElement('div');
        div.classList.add('split-line');
        div.setAttribute('id', `form-${newFormIndex}`); 
        div.setAttribute('data-form-index', newFormIndex);

        div.innerHTML = `
            <input type="hidden" name="${formPrefix}-${newFormIndex}-id" id="id_${formPrefix}-${newFormIndex}-id">
            <input type="text" name="${formPrefix}-${newFormIndex}-description" id="id_${formPrefix}-${newFormIndex}-description" placeholder="Description" required class="p-2 border rounded-md w-full">
            <input type="number" name="${formPrefix}-${newFormIndex}-amount" id="id_${formPrefix}-${newFormIndex}-amount" step="0.01" placeholder="Montant" required class="p-2 border rounded-md w-full">
            <div>
                <select name="${formPrefix}-${newFormIndex}-main_category" id="id_${formPrefix}-${newFormIndex}-main_category" class="p-2 border rounded-md w-full split-category-main" required>
                    <option value="">Sélectionner Catégorie Principale</option>
                </select>
                <select name="${formPrefix}-${newFormIndex}-subcategory" id="id_${formPrefix}-${newFormIndex}-subcategory" class="p-2 border rounded-md w-full split-category subcategory-hidden">
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
        totalFormsInput.value = newFormIndex + 1;

        const descriptionInput = div.querySelector(`#id_${formPrefix}-${newFormIndex}-description`);
        const amountInput = div.querySelector(`#id_${formPrefix}-${newFormIndex}-amount`);
        const mainCategorySelect = div.querySelector(`#id_${formPrefix}-${newFormIndex}-main_category`);
        const subcategorySelect = div.querySelector(`#id_${formPrefix}-${newFormIndex}-subcategory`);

        if (descriptionInput) descriptionInput.value = initialData.description || '';
        if (amountInput) amountInput.value = (initialData.amount !== undefined && initialData.amount !== null) ? parseFloat(initialData.amount).toFixed(2) : '';
        
        if (mainCategorySelect) {
            populateMainCategories(mainCategorySelect, allCategories, initialData.main_category);
            if (initialData.subcategory && mainCategorySelect.value) { 
                populateSubcategories(mainCategorySelect.value, subcategorySelect, initialData.subcategory);
            }
        }

        addSplitLineEventListeners(div);
        calculateRemainingAmount();

        return div;
    }

    /**
     * Attache les écouteurs d'événements nécessaires à une ligne de division.
     * @param {HTMLElement} lineElement The DOM element de la ligne de division.
     */
    function addSplitLineEventListeners(lineElement) {
        const formIndex = lineElement.dataset.formIndex;
        const formPrefix = 'split_lines';

        const amountInput = lineElement.querySelector(`#id_${formPrefix}-${formIndex}-amount`);
        const deleteBtn = lineElement.querySelector('.delete-split-btn');
        const mainCategorySelect = lineElement.querySelector(`#id_${formPrefix}-${formIndex}-main_category`);
        const subCategorySelect = lineElement.querySelector(`#id_${formPrefix}-${formIndex}-subcategory`);
        const deleteCheckbox = lineElement.querySelector(`#id_${formPrefix}-${formIndex}-DELETE`);
        const descriptionInput = lineElement.querySelector(`#id_${formPrefix}-${formIndex}-description`);


        if (amountInput) {
            amountInput.addEventListener('input', calculateRemainingAmount);
            amountInput.addEventListener('blur', function() {
                if (this.value !== '') {
                    this.value = parseFloat(this.value.replace(',', '.')).toFixed(2);
                }
            });
        }

        if (deleteBtn && deleteCheckbox) {
            deleteBtn.addEventListener('click', function() {
                lineElement.style.display = 'none';
                deleteCheckbox.checked = true;
                calculateRemainingAmount();
                updateSubmitButtonState(); 
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

        if (descriptionInput) {
            let debounceTimeout;
            descriptionInput.addEventListener('input', () => {
                clearTimeout(debounceTimeout);
                debounceTimeout = setTimeout(() => {
                    calculateRemainingAmount();
                }, 300);
            });
        }
    }

    /**
     * Initializes category and subcategory dropdowns for a given split line.
     * Manages loading subcategories and initial selection if an initialSubcategoryId is provided.
     * @param {HTMLElement} splitLineElement The DOM element of the split line.
     */
    function initializeSplitCategoryDropdowns(splitLineElement) {
        const formIndex = splitLineElement.dataset.formIndex;
        const formPrefix = 'split_lines';

        const mainCategorySelect = splitLineElement.querySelector(`#id_${formPrefix}-${formIndex}-main_category`);
        const subCategorySelect = splitLineElement.querySelector(`#id_${formPrefix}-${formIndex}-subcategory`);
        
        const initialMainCategoryValue = mainCategorySelect?.value; 
        populateMainCategories(mainCategorySelect, allCategories, initialMainCategoryValue);

        const initialSubcategoryId = subCategorySelect?.value; 

        if (mainCategorySelect?.value) { 
            populateSubcategories(mainCategorySelect.value, subCategorySelect, initialSubcategoryId);
        } else {
            subCategorySelect?.classList.add('subcategory-hidden'); 
        }
        updateCategoryIconDisplay(mainCategorySelect);
    }


    /**
     * Calculates the remaining amount to split and updates the summary display.
     * Also manages button visibility and prompts.
     */
    function calculateRemainingAmount() {
        let currentSplitSum = 0;
        const splitAmountInputs = document.querySelectorAll('.split-line:not([style*="display: none"]) input[name$="-amount"]');
        splitAmountInputs.forEach(input => {
            let value = parseFloat(input.value.replace(',', '.')) || 0; 
            currentSplitSum += value;
        });

        let remaining = originalTransactionAmount - currentSplitSum;
        remainingAmountSpan.textContent = remaining.toFixed(2);

        splitSummaryBox.classList.remove('balanced', 'negative-remaining', 'positive-remaining');
        splitGuidanceText.classList.remove('text-red-500', 'text-green-500', 'text-gray-600'); 

        if (Math.abs(remaining) < 0.01) { // Utiliser une tolérance pour la comparaison à zéro
            splitSummaryBox.classList.add('balanced');
            splitGuidanceText.textContent = "Le montant est entièrement divisé. Vous pouvez maintenant valider.";
            splitGuidanceText.classList.add('text-green-500');
        } else if (remaining < 0) {
            splitSummaryBox.classList.add('negative-remaining');
            splitGuidanceText.textContent = `Attention : Vous avez alloué ${Math.abs(remaining).toFixed(2)} CHF de trop !`;
            splitGuidanceText.classList.add('text-red-500');
        } else {
            splitSummaryBox.classList.add('positive-remaining');
            splitGuidanceText.textContent = `Il reste ${remaining.toFixed(2)} CHF à diviser.`;
            splitGuidanceText.classList.add('text-gray-600'); 
        }

        updateAddLineOrPrefillLogic(); 
        updateSubmitButtonState(); 
    }

    /**
     * Gère la logique d'ajout automatique de ligne ou de pré-remplissage.
     */
    function updateAddLineOrPrefillLogic() {
        const activeLines = document.querySelectorAll('.split-line:not([style*="display: none"])');
        const currentRemaining = parseFloat(remainingAmountSpan.textContent);
        const lastActiveLine = activeLines[activeLines.length - 1];
    
        // Si le montant est balancé, cacher le bouton d'ajout de ligne
        if (Math.abs(currentRemaining) < 0.01) {
            addSplitLineBtn.classList.add('hidden'); 
            return;
        }

        // Si la dernière ligne est remplie et qu'il reste du montant, ajouter une nouvelle ligne
        if (lastActiveLine) {
            const amountInput = lastActiveLine.querySelector('input[name$="-amount"]');
            const descriptionInput = lastActiveLine.querySelector('input[name$="-description"]');
            const mainCategorySelect = lastActiveLine.querySelector('select[name$="-main_category"]');
            const subcategorySelect = lastActiveLine.querySelector('select[name$="-subcategory"]');
    
            const isLastLineFilled = (amountInput && parseFloat(amountInput.value.replace(',', '.')) > 0) && 
                                     (descriptionInput && descriptionInput.value.trim() !== '') &&
                                     (mainCategorySelect && mainCategorySelect.value !== '') &&
                                     (subcategorySelect ? subcategorySelect.value !== '' || subcategorySelect.classList.contains('subcategory-hidden') : true);
            
            // Vérifier s'il n'y a pas déjà une ligne vide non supprimée juste après la dernière active
            const lastLineIndex = parseInt(lastActiveLine.dataset.formIndex);
            const nextFormIndex = lastLineIndex + 1;
            const nextLineElement = document.getElementById(`form-${nextFormIndex}`);
            const nextLineIsActive = nextLineElement && !nextLineElement.querySelector('input[name$="-DELETE"]')?.checked;
            
            if (isLastLineFilled && !nextLineIsActive) {
                const newSplitLine = createSplitLine({
                    description: originalDescription, // Pré-remplir la description avec l'originale
                    amount: currentRemaining.toFixed(2) 
                });
                if (newSplitLine) { 
                    newSplitLine.querySelector('input[name$="-description"]').focus(); 
                }
            } else if (isLastLineFilled && nextLineIsActive) {
                // Si la dernière ligne est remplie, il reste du montant, et la ligne suivante existe et est active,
                // alors on met à jour le montant de cette ligne suivante avec le restant.
                const nextLineAmountInput = nextLineElement.querySelector('input[name$="-amount"]');
                if (nextLineAmountInput) {
                    nextLineAmountInput.value = currentRemaining.toFixed(2);
                }
            }
        }
    }

    /**
     * Met à jour l'état activé/désactivé du bouton de soumission.
     */
    function updateSubmitButtonState() {
        const currentRemaining = parseFloat(remainingAmountSpan.textContent);
        const activeLines = document.querySelectorAll('.split-line:not([style*="display: none"])');

        let allActiveLinesValid = true;
        if (activeLines.length === 0) {
            allActiveLinesValid = false; 
        } else {
            activeLines.forEach(line => {
                const descriptionInput = line.querySelector('input[name$="-description"]');
                const amountInput = line.querySelector('input[name$="-amount"]');
                const mainCategorySelect = line.querySelector('select[name$="-main_category"]');
                const subcategorySelect = line.querySelector('select[name$="-subcategory"]');
    
                const isDescriptionValid = descriptionInput && descriptionInput.value.trim() !== '';
                const isAmountValid = amountInput && parseFloat(amountInput.value.replace(',', '.')) > 0; 
                const isMainCategorySelected = mainCategorySelect && mainCategorySelect.value !== '';
                const isSubcategoryValid = (subcategorySelect && !subcategorySelect.classList.contains('subcategory-hidden')) ? subcategorySelect.value !== '' : true; 
    
                if (!isDescriptionValid || !isAmountValid || !isMainCategorySelected || !isSubcategoryValid) {
                    allActiveLinesValid = false;
                    line.classList.add('has-error'); 
                } else {
                    line.classList.remove('has-error'); 
                }
            });
        }
    
        // Le bouton est activé si le montant restant est quasi nul ET toutes les lignes actives sont valides
        if (Math.abs(currentRemaining) < 0.01 && allActiveLinesValid) {
            mainSubmitBtn.disabled = false;
            mainSubmitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            mainSubmitBtn.disabled = true;
            mainSubmitBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }


    // --- Initialization on page load ---
    const prefilledLines = document.querySelectorAll('.split-line');
    if (prefilledLines.length > 0) {
        prefilledLines.forEach(line => {
            addSplitLineEventListeners(line);
            initializeSplitCategoryDropdowns(line);
        });
        calculateRemainingAmount(); 
    } else {
        // Si aucune ligne n'est pré-remplie (premier chargement), créer la première ligne
        createSplitLine({
            description: originalDescription, 
            amount: '' 
        });
    }

    if (addSplitLineBtn) {
        addSplitLineBtn.addEventListener('click', () => {
            const newLine = createSplitLine();
            if (newLine) {
                newLine.querySelector('input[name$="-description"]').focus();
            }
        });
    }

    // Gestion de la soumission du formulaire (remplace les alertes par des toasts)
    if (splitTransactionForm) {
        splitTransactionForm.addEventListener('submit', function(event) {
            const currentRemaining = parseFloat(remainingAmountSpan.textContent);
            if (Math.abs(currentRemaining) > 0.01) { 
                event.preventDefault(); 
                if (typeof showToast !== 'undefined') { 
                    showToast("La somme des montants divisés ne correspond pas exactement au montant original. Veuillez ajuster avant de soumettre.", 'error');
                } else {
                    alert("Attention: La somme des montants divisés ne correspond pas exactement au montant original. Veuillez ajuster avant de soumettre.");
                }
                return; 
            }

            const activeLines = document.querySelectorAll('.split-line:not([style*="display: none"])');
            let allLinesValid = true;
            if (activeLines.length === 0) {
                allLinesValid = false;
            }

            activeLines.forEach(line => {
                const descriptionInput = line.querySelector('input[name$="-description"]');
                const amountInput = line.querySelector('input[name$="-amount"]');
                const mainCategorySelect = line.querySelector('select[name$="-main_category"]');
                const subcategorySelect = line.querySelector('select[name$="-subcategory"]');

                line.classList.remove('has-error'); 

                const isDescriptionValid = descriptionInput && descriptionInput.value.trim() !== '';
                const isAmountValid = amountInput && parseFloat(amountInput.value.replace(',', '.')) > 0; 
                const isMainCategorySelected = mainCategorySelect && mainCategorySelect.value !== '';
                const isSubcategoryValid = (subcategorySelect && !subcategorySelect.classList.contains('subcategory-hidden')) ? subcategorySelect.value !== '' : true;
                
                if (!isDescriptionValid || !isAmountValid || !isMainCategorySelected || !isSubcategoryValid) {
                    allLinesValid = false;
                    line.classList.add('has-error');
                }
            });

            if (!allLinesValid) {
                event.preventDefault(); 
                if (typeof showToast !== 'undefined') { 
                    showToast("Veuillez remplir toutes les informations requises (description, montant, catégorie) pour chaque ligne de division.", 'error');
                } else {
                    alert("Veuillez remplir toutes les informations requises (description, montant, catégorie) pour chaque ligne de division.");
                }
            }
        });
    }

    calculateRemainingAmount(); // Ceci déclenchera updateAddLineOrPrefillLogic et updateSubmitButtonState.
});
