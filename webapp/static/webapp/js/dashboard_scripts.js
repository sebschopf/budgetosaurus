// webapp/static/webapp/js/dashboard_scripts.js

document.addEventListener('DOMContentLoaded', function() {
    const categorySelect = document.getElementById('id_category');
    const subcategorySelect = document.getElementById('id_subcategory');
    const subcategoryContainer = document.getElementById('subcategory-field-container');
    const accountSelect = document.getElementById('id_account');
    const descriptionInput = document.getElementById('id_description');
    const commonDescriptionsList = document.getElementById('commonDescriptionsList');

    const dateInput = document.getElementById('id_date');
    const todayBtn = document.getElementById('today-date-btn');
    const yesterdayBtn = document.getElementById('yesterday-date-btn');

    const LAST_ACCOUNT_KEY = 'lastSelectedAccount';

    // Éléments pour la suppression par lot
    const selectAllCheckbox = document.getElementById('select-all-transactions');
    const transactionCheckboxes = document.querySelectorAll('.transaction-checkbox');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const transactionsForm = document.getElementById('transactions-form');

    // Récupérer les données de catégorie et sous-catégorie du DOM
    const allCategories = JSON.parse(document.getElementById('allCategoriesData').textContent);
    const allSubcategories = JSON.parse(document.getElementById('allSubcategoriesData').textContent);

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
     * Peuple le dropdown des catégories principales.
     * @param {HTMLElement} selectElement L'élément <select> à peupler.
     * @param {Array} categoriesData Les données des catégories.
     * @param {string|number|null} initialValue La valeur initiale à sélectionner.
     */
    function populateMainCategories(selectElement, categoriesData, initialValue = null) {
        selectElement.innerHTML = '<option value="">Sélectionner Catégorie Principale</option>';
        categoriesData.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name; // Texte de l'option sans HTML
            option.dataset.isFundManaged = category.is_fund_managed;
            option.dataset.isBudgeted = category.is_budgeted;
            option.dataset.isGoalLinked = category.is_goal_linked;
            selectElement.appendChild(option);
        });
        if (initialValue) {
            selectElement.value = initialValue;
        }
        // Déclencher le changement pour mettre à jour les sous-catégories et l'affichage initial de l'icône
        selectElement.dispatchEvent(new Event('change'));
    }

    /**
     * Peuple le dropdown des sous-catégories en fonction de la catégorie parente sélectionnée.
     * @param {string} parentCategoryId L'ID de la catégorie parente.
     * @param {HTMLElement} subcategorySelectElement L'élément <select> des sous-catégories.
     * @param {string|null} initialSubcategoryId L'ID de la sous-catégorie à pré-sélectionner.
     */
    function populateSubcategories(parentCategoryId, subcategorySelectElement, initialSubcategoryId = null) {
        subcategorySelectElement.innerHTML = '<option value="">Sélectionner une sous-catégorie</option>';
        const childrenOfParent = allSubcategories.filter(cat => cat.parent === parseInt(parentCategoryId));

        if (childrenOfParent.length > 0) {
            childrenOfParent.forEach(subcategory => {
                const option = document.createElement('option');
                option.value = subcategory.id;
                option.textContent = subcategory.name; // Texte de l'option sans HTML
                option.dataset.isFundManaged = subcategory.is_fund_managed;
                option.dataset.isBudgeted = subcategory.is_budgeted;
                option.dataset.isGoalLinked = subcategory.is_goal_linked;
                subcategorySelectElement.appendChild(option);
            });
            subcategoryContainer.style.display = 'block'; // Afficher le champ
        } else {
            subcategoryContainer.style.display = 'none'; // Cacher le champ
        }

        if (initialSubcategoryId) {
            // S'assurer que l'option existe avant de tenter de la sélectionner
            const optionExists = Array.from(subcategorySelectElement.options).some(option => option.value == initialSubcategoryId);
            if (optionExists) {
                subcategorySelectElement.value = initialSubcategoryId;
            }
        }
        // Met à jour l'icône affichée à côté du champ select
        updateCategoryIconDisplay(subcategorySelectElement);
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


    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    todayBtn.addEventListener('click', function() {
        dateInput.value = formatDate(new Date());
    });

    yesterdayBtn.addEventListener('click', function() {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        dateInput.value = formatDate(yesterday);
    });

    function loadCommonDescriptions() {
        fetch(`/get-common-descriptions/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('La réponse du réseau pour les descriptions n\'était pas ok.');
                }
                return response.json();
            })
            .then(data => {
                commonDescriptionsList.innerHTML = '';
                data.forEach(description => {
                    const option = document.createElement('option');
                    option.value = description;
                    commonDescriptionsList.appendChild(option);
                });
            })
            .catch(error => {
                console.error('Erreur lors du chargement des descriptions courantes:', error);
            });
    }

    // Event listener for main category change
    categorySelect.addEventListener('change', function() {
        const selectedParentId = this.value;
        populateSubcategories(selectedParentId, subcategorySelect);
        updateCategoryIconDisplay(this); // Update icon for main category
    });

    // Event listener for subcategory change
    subcategorySelect.addEventListener('change', function() {
        updateCategoryIconDisplay(this); // Update icon for subcategory
    });


    const lastSelectedAccountId = localStorage.getItem(LAST_ACCOUNT_KEY);
    if (lastSelectedAccountId) {
        const optionExists = Array.from(accountSelect.options).some(option => option.value === lastSelectedAccountId);
        if (optionExists) {
            accountSelect.value = lastSelectedAccountId;
        }
    }

    accountSelect.addEventListener('change', function() {
        localStorage.setItem(LAST_ACCOUNT_KEY, this.value);
    });

    // Initial population and icon display
    populateMainCategories(categorySelect, allCategories, categorySelect.value);
    // Si une sous-catégorie était déjà sélectionnée (e.g. après une erreur de formulaire),
    // populateSubcategories sera appelée par le changement de categorySelect et la resélectionnera.
    // Assurons un affichage initial des flags pour la sous-catégorie si elle est déjà pré-remplie.
    if (subcategorySelect.value) {
        updateCategoryIconDisplay(subcategorySelect);
    }


    if (!categorySelect.value) { // If no main category is initially selected, hide subcategory dropdown
        subcategoryContainer.style.display = 'none';
    }


    loadCommonDescriptions();

    // --- Logique pour la suggestion de catégorisation (Fuzzy Matching) ---
    let suggestionTimeout;
    descriptionInput.addEventListener('input', function() {
        clearTimeout(suggestionTimeout); // Annule le précédent timeout
        const description = this.value.trim();

        if (description.length < 3) { // Ne suggère pas pour des descriptions trop courtes
            return;
        }

        suggestionTimeout = setTimeout(() => {
            fetch(`/suggest-categorization/?description=${encodeURIComponent(description)}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Erreur lors de la suggestion de catégorisation.');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.category_id) {
                        // Mettre à jour la catégorie principale
                        categorySelect.value = data.category_id;

                        // Charger les sous-catégories si une sous-catégorie est suggérée
                        if (data.subcategory_id) {
                            // Pass initial subcategory value directly to populateSubcategories
                            populateSubcategories(data.category_id, subcategorySelect, data.subcategory_id);
                        } else {
                            // Si seule une catégorie principale est suggérée, s'assurer que la sous-catégorie est vide/cachée
                            subcategorySelect.innerHTML = '<option value="">Sélectionner une sous-catégorie</option>';
                            subcategoryContainer.style.display = 'none';
                            updateCategoryIconDisplay(subcategorySelect); // Clear icon if subcategory is hidden
                        }

                        // Update icon for main category after setting its value
                        updateCategoryIconDisplay(categorySelect);

                        // Mettre à jour les tags
                        const tagsCheckboxes = document.querySelectorAll('input[name="tags"]');
                        tagsCheckboxes.forEach(checkbox => {
                            checkbox.checked = data.tag_ids.includes(parseInt(checkbox.value));
                        });

                        console.log('Suggestion appliquée:', data);
                    } else {
                        // Si aucune suggestion, on ne fait rien pour ne pas effacer la saisie de l'utilisateur
                        console.log('Aucune suggestion trouvée.');
                    }
                })
                .catch(error => {
                    console.error('Erreur lors de la suggestion:', error);
                });
        }, 500); // Délai de 500ms après la dernière frappe
    });
    // --- Fin de la logique de suggestion ---


    // --- Logique pour la suppression par lot ---
    function updateDeleteButtonVisibility() {
        const anyCheckboxChecked = Array.from(transactionCheckboxes).some(cb => cb.checked);
        if (anyCheckboxChecked) {
            deleteSelectedBtn.classList.remove('hidden');
        } else {
            deleteSelectedBtn.classList.add('hidden');
        }
    }

    // Gérer la case à cocher "Tout sélectionner"
    selectAllCheckbox.addEventListener('change', function() {
        transactionCheckboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
        updateDeleteButtonVisibility();
    });

    // Gérer les cases à cocher individuelles
    transactionCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (!this.checked) {
                selectAllCheckbox.checked = false;
            }
            updateDeleteButtonVisibility();
        });
    });

    // Gérer le bouton "Supprimer la sélection"
    deleteSelectedBtn.addEventListener('click', function(e) {
        e.preventDefault();
        const selectedIds = Array.from(transactionCheckboxes)
                            .filter(cb => cb.checked)
                            .map(cb => cb.value);

        if (selectedIds.length === 0) {
            // Utilisez votre fonction de toast pour les messages d'information
            if (typeof showToast !== 'undefined') {
                showToast("Veuillez sélectionner au moins une transaction à supprimer.", 'info');
            } else {
                alert("Veuillez sélectionner au moins une transaction à supprimer.");
            }
            return;
        }

        // Utilisez votre fonction de modale de confirmation personnalisée
        showConfirmationModal(
            "Confirmer la suppression",
            `Êtes-vous sûr de vouloir supprimer les ${selectedIds.length} transaction(s) sélectionnée(s) ?`,
            (confirmed) => {
                if (confirmed) {
                    const tempForm = document.createElement('form');
                    tempForm.method = 'POST';
                    tempForm.action = '{% url "delete_selected_transactions" %}';
                    tempForm.style.display = 'none';

                    const csrfInput = document.createElement('input');
                    csrfInput.type = 'hidden';
                    csrfInput.name = 'csrfmiddlewaretoken';
                    csrfInput.value = document.querySelector('[name=csrfmiddlewaretoken]').value;
                    tempForm.appendChild(csrfInput);

                    selectedIds.forEach(id => {
                        const input = document.createElement('input');
                        input.type = 'hidden';
                        input.name = 'transaction_ids';
                        input.value = id;
                        tempForm.appendChild(input);
                    });

                    document.body.appendChild(tempForm);
                    tempForm.submit();
                }
            }
        );
    });

    // Initialiser la visibilité du bouton au chargement
    updateDeleteButtonVisibility();
    // --- Fin de la logique pour la suppression par lot ---
});
