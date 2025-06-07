// webapp/static/webapp/js/debit_funds.js

document.addEventListener('DOMContentLoaded', function() {
    // Vérifier si l'élément de transaction originale existe avant d'initialiser le JS
    const originalTransactionInfoElement = document.querySelector('.original-transaction-info');
    if (!originalTransactionInfoElement) {
        console.log("Aucune transaction originale trouvée pour le débit de fonds. Initialisation JS ignorée.");
        return; 
    }

    // Le montant de la transaction originale est négatif pour une dépense.
    // Nous utilisons sa valeur absolue pour les calculs de répartition.
    const originalTransactionAmount = Math.abs(parseFloat(document.getElementById('originalTransactionAmountData').textContent));

    const debitLinesContainer = document.getElementById('debit-lines-container');
    const addDebitLineBtn = document.getElementById('add-debit-line-btn');
    const debitSummaryBox = document.getElementById('debit-summary-box');
    const remainingAmountSpan = document.getElementById('remaining-amount');
    const debitFundsForm = document.getElementById('debitFundsForm');

    // Récupérer les données des catégories gérées par fonds du DOM
    const fundManagedCategories = JSON.parse(document.getElementById('fundManagedCategoriesData').textContent);
    
    // Gérer le compteur total de formulaires pour le formset
    const totalFormsInput = document.querySelector('#id_form-TOTAL_FORMS'); // Note : le préfixe du formset peut être 'form' par défaut si non spécifié
    const initialFormsInput = document.querySelector('#id_form-INITIAL_FORMS');
    // const maxNumFormsInput = document.querySelector('#id_form-MAX_NUM_FORMS'); // Pas strictement nécessaire pour les fonctionnalités côté client

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
     * Remplit la liste déroulante des catégories pour une ligne de débit avec des icônes.
     * @param {HTMLElement} selectElement L'élément <select> à remplir.
     * @param {Array} categoriesData Les données des catégories gérées par fonds.
     * @param {string|number|null} initialValue La valeur initiale à sélectionner.
     */
    function populateCategoryDropdown(selectElement, categoriesData, initialValue = null) {
        selectElement.innerHTML = '<option value="">Sélectionner le Fonds (Catégorie)</option>';
        categoriesData.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            // Le texte de l'option sera juste le nom de la catégorie
            option.textContent = category.name;
            // Les flags sont stockés dans les dataset de l'option
            option.dataset.isFundManaged = category.is_fund_managed; 
            option.dataset.isBudgeted = category.is_budgeted || false; 
            option.dataset.isGoalLinked = category.is_goal_linked || false; 
            selectElement.appendChild(option);
        });
        if (initialValue) {
            selectElement.value = initialValue;
        }
        // Déclencher le changement pour mettre à jour l'icône affichée à côté du champ select
        selectElement.dispatchEvent(new Event('change'));
    }

    /**
     * Ajoute ou met à jour les icônes d'information de la catégorie à côté de l'élément select.
     * Permet d'afficher plusieurs badges (Fonds, Budget, Objectif).
     * @param {HTMLElement} selectElement L'élément <select> de la catégorie.
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
        if (selectedOption && selectedOption.value) { // N'ajouter que si une catégorie réelle est sélectionnée
            const isFundManaged = selectedOption.dataset.isFundManaged === 'true'; // 'true' est une chaîne de caractères du dataset
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
        }
    }

    /**
     * Crée et ajoute une nouvelle ligne de débit au formulaire (compatible formset).
     */
    function createDebitLine() {
        const currentTotalForms = parseInt(totalFormsInput.value);
        const newFormIndex = currentTotalForms;

        const div = document.createElement('div');
        div.classList.add('debit-line');
        div.setAttribute('id', `form-${newFormIndex}`); // Important pour le JS du formset (le préfixe par défaut est 'form')

        const formPrefix = 'form'; // Préfixe de formset par défaut dans Django, sauf spécification contraire
        div.innerHTML = `
            <input type="hidden" name="${formPrefix}-${newFormIndex}-id" id="id_${formPrefix}-${newFormIndex}-id">
            <div>
                <select name="${formPrefix}-${newFormIndex}-category" id="id_${formPrefix}-${newFormIndex}-category" required class="p-2 border rounded-md w-full split-category-main">
                    <option value="">Sélectionner le Fonds (Catégorie)</option>
                </select>
            </div>
            <input type="number" name="${formPrefix}-${newFormIndex}-amount" id="id_${formPrefix}-${newFormIndex}-amount" step="0.01" placeholder="Montant à débiter" required class="p-2 border rounded-md w-full">
            <input type="text" name="${formPrefix}-${newFormIndex}-notes" id="id_${formPrefix}-${newFormIndex}-notes" placeholder="Notes (optionnel)" class="p-2 border rounded-md w-full">
            <div class="flex items-center justify-center">
                <input type="checkbox" name="${formPrefix}-${newFormIndex}-DELETE" id="id_${formPrefix}-${newFormIndex}-DELETE" class="hidden-delete-checkbox">
                <label for="id_${formPrefix}-${newFormIndex}-DELETE" class="sr-only">Supprimer</label>
                <button type="button" class="delete-line-btn">X</button>
            </div>
        `;
        
        debitLinesContainer.appendChild(div);
        totalFormsInput.value = newFormIndex + 1; // Mettre à jour TOTAL_FORMS

        addDebitLineEventListeners(div); // Attacher les événements à la nouvelle ligne
        initializeDebitCategoryDropdowns(div); // Initialiser les listes déroulantes pour la nouvelle ligne
        calculateRemainingAmount(); // Recalculer après l'ajout
    }

    /**
     * Attache les écouteurs d'événements nécessaires à une ligne de débit.
     * @param {HTMLElement} lineElement L'élément DOM de la ligne de débit.
     */
    function addDebitLineEventListeners(lineElement) {
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
     * Initialise les listes déroulantes de catégories pour une ligne de débit donnée.
     * @param {HTMLElement} debitLineElement L'élément DOM de la ligne de débit.
     */
    function initializeDebitCategoryDropdowns(debitLineElement) {
        const categorySelect = debitLineElement.querySelector('select[name$="-category"]');
        
        const initialCategoryValue = categorySelect.value; // Obtenir la valeur initiale du formulaire Django
        populateCategoryDropdown(categorySelect, fundManagedCategories, initialCategoryValue);
        // Assurer que les flags s'affichent au chargement si une catégorie est déjà sélectionnée
        if (categorySelect.value) {
            updateCategoryIconDisplay(categorySelect);
        }
    }


    /**
     * Calcule le montant restant à débiter et met à jour l'affichage du résumé.
     */
    function calculateRemainingAmount() {
        let currentDebitedSum = 0;
        // Sélectionne toutes les entrées de montant POUR LES LIGNES NON MARQUÉES POUR SUPPRESSION
        const debitedAmountInputs = document.querySelectorAll('.debit-line:not([style*="display: none"]) input[name$="-amount"]');
        debitedAmountInputs.forEach(input => {
            let value = parseFloat(input.value.replace(',', '.')) || 0;
            currentDebitedSum += value; // Les montants pour le débit doivent être positifs
        });

        // Le montant restant est la différence entre le montant original de la dépense (valeur absolue)
        // et la somme des montants débités des fonds.
        let remaining = originalTransactionAmount - currentDebitedSum;
        remainingAmountSpan.textContent = remaining.toFixed(2);
        debitSummaryBox.classList.remove('balanced'); // Réinitialiser la classe balanced
        
        // Ajouter une petite tolérance pour les comparaisons en virgule flottante
        if (Math.abs(remaining) < 0.01) { 
            debitSummaryBox.classList.add('balanced');
        }

        remainingAmountSpan.classList.remove('positive', 'negative');
        if (remaining > 0.01) {
            remainingAmountSpan.classList.add('positive');
        } else if (remaining < -0.01) {
            remainingAmountSpan.classList.add('negative');
            // Ajouter un indicateur visuel ou un avertissement si le débit dépasse la transaction originale
            debitSummaryBox.classList.remove('balanced');
            debitSummaryBox.classList.add('has-error'); // Vous pouvez vouloir une classe d'erreur spécifique pour cette boîte
        } else {
            debitSummaryBox.classList.remove('has-error');
        }
    }

    // --- Initialisation au chargement de la page ---
    // Attacher les événements aux lignes du formset existantes (y compris celles pré-remplies par Django)
    document.querySelectorAll('.debit-line').forEach(line => {
        addDebitLineEventListeners(line);
        initializeDebitCategoryDropdowns(line);
    });

    if (addDebitLineBtn) {
        addDebitLineBtn.addEventListener('click', createDebitLine);
    }

    calculateRemainingAmount(); // Calcul initial

    // Gérer la soumission du formulaire de débit de fonds
    if (debitFundsForm) {
        debitFundsForm.addEventListener('submit', function(event) {
            // Validation finale côté client, basée sur le calcul du montant restant
            let currentRemaining = parseFloat(remainingAmountSpan.textContent);
            if (currentRemaining < -0.01) { // Vérifier si le débit dépasse le montant de la transaction originale
                event.preventDefault(); 
                // Utiliser votre fonction de toast pour les messages d'erreur
                if (typeof showToast !== 'undefined') {
                    showToast("Attention : Le montant total débité dépasse le montant de la transaction originale. Veuillez ajuster avant de soumettre.", 'error');
                } else {
                    alert("Attention : Le montant total débité dépasse le montant de la transaction originale. Veuillez ajuster avant de soumettre.");
                }
                return; 
            }

            // Validation côté client : S'assurer que chaque ligne non supprimée a une catégorie et un montant
            const lines = debitLinesContainer.querySelectorAll('.debit-line:not([style*="display: none"])');
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
                // Utiliser votre fonction de toast pour les messages d'erreur
                if (typeof showToast !== 'undefined') {
                    showToast("Veuillez remplir toutes les informations requises (Fonds/Enveloppe, Montant) pour chaque ligne de débit.", 'error');
                } else {
                    alert("Veuillez remplir toutes les informations requises (Fonds/Enveloppe, Montant) pour chaque ligne de débit.");
                }
            }
            // Le reste de la validation est géré côté serveur par le formset.
        });
    }
});
