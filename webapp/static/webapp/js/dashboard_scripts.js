// webapp/static/webapp/js/dashboard_scripts.js

/**
 * Composant Alpine.js pour la gestion du formulaire d'ajout/édition de transaction.
 * Encapsule l'état réactif et les méthodes pour l'interactivité du formulaire.
 *
 * @returns {Object} L'objet de configuration du composant Alpine.js.
 */
function transactionForm() {
    // Récupération des données initiales depuis le DOM (passées via Django json_script)
    const allCategoriesDataElement = document.getElementById('allCategoriesData');
    const allSubcategoriesDataElement = document.getElementById('allSubcategoriesData');
    
    // Assurez-vous que ces données sont correctement parsées, ou utilisez des tableaux vides par défaut.
    const allCategories = allCategoriesDataElement ? JSON.parse(allCategoriesDataElement.textContent) : [];
    const allSubcategories = allSubcategoriesDataElement ? JSON.parse(allSubcategoriesDataElement.textContent) : [];

    // Récupération des valeurs initiales des champs de formulaire
    const initialValues = {
        date: document.getElementById('id_date')?.value || '',
        description: document.getElementById('id_description')?.value || '',
        amount: parseFloat(document.getElementById('id_amount')?.value) || null,
        category: document.getElementById('id_category')?.value || '',
        subcategory: document.getElementById('id_subcategory')?.value || '',
        account: document.getElementById('id_account')?.value || '',
        transactionType: document.getElementById('id_transaction_type')?.value || 'expense', // Valeur par défaut
        tags: Array.from(document.querySelectorAll('input[name="tags"]:checked'))
                   .map(cb => parseInt(cb.value))
    };

    const LAST_ACCOUNT_KEY = 'lastSelectedAccount';

    return {
        // --- PROPRIÉTÉS RÉACTIVES (ÉTAT DU COMPOSANT) ---
        date: initialValues.date,
        description: initialValues.description,
        amount: initialValues.amount,
        selectedCategory: initialValues.category,
        selectedSubcategory: initialValues.subcategory,
        selectedAccount: initialValues.account,
        transactionType: initialValues.transactionType,
        selectedTags: initialValues.tags,
        
        allCategories: allCategories, // Utilisé pour findCategoryById et hasSubcategoriesForSelectedCategory
        allSubcategories: allSubcategories, // Utilisé pour filteredSubcategories
        commonDescriptions: [],
        
        isLoadingSuggestion: false, // Indicateur de chargement pour les suggestions AJAX
        formSubmitted: false, // Indique si le formulaire a été soumis au moins une fois (pour la validation visuelle)

        // --- PROPRIÉTÉS CALCULÉES (GETTERS) ---

        /**
         * Retourne les sous-catégories filtrées par la catégorie principale.
         * Note: Avec le rendu des options par Django, cette fonction est principalement utilisée
         * pour déterminer la visibilité du champ de sous-catégorie (`hasSubcategoriesForSelectedCategory`).
         * Elle ne peuple plus directement les <option> du DOM.
         * @returns {Array<Object>} Liste des sous-catégories pertinentes.
         */
        get filteredSubcategories() {
            if (!this.selectedCategory) {
                return [];
            }
            // Retourne toutes les sous-catégories qui ont le parent sélectionné
            return this.allSubcategories.filter(cat => cat.parent === parseInt(this.selectedCategory));
        },

        /**
         * Indique si la catégorie principale sélectionnée a des sous-catégories.
         * @returns {boolean} True si des sous-catégories existent pour la catégorie sélectionnée.
         */
        get hasSubcategoriesForSelectedCategory() {
            return this.filteredSubcategories.length > 0;
        },

        // --- MÉTHODES DU COMPOSANT ---

        /**
         * Méthode d'initialisation du composant. Appelé automatiquement par Alpine.js via `x-init`.
         */
        init() {
            this.loadLastAccount();
            this.loadCommonDescriptions();

            // S'assurer que le champ de sous-catégorie est correctement affiché/masqué
            // et que la valeur de la sous-catégorie est valide pour la catégorie parente initiale.
            this.$nextTick(() => {
                if (this.selectedCategory) {
                    if (this.hasSubcategoriesForSelectedCategory) {
                        // Si une sous-catégorie est pré-sélectionnée mais n'est pas valide pour le parent
                        if (this.selectedSubcategory && !this.filteredSubcategories.some(cat => cat.id === parseInt(this.selectedSubcategory))) {
                            this.selectedSubcategory = ''; // Réinitialiser
                        }
                    } else {
                        this.selectedSubcategory = ''; // Si pas de sous-catégories pour le parent, effacer la sous-catégorie
                    }
                }
            });

            this.$watch('description', (value) => {
                if (value && value.length >= 3) {
                    this.suggestCategorization(value);
                }
            });
        },

        /**
         * Réinitialise tous les champs du formulaire.
         */
        clearForm() {
            this.date = '';
            this.description = '';
            this.amount = null;
            this.selectedCategory = '';
            this.selectedSubcategory = '';
            this.loadLastAccount(); // Réinitialise le compte au dernier utilisé
            this.transactionType = 'expense'; 
            this.selectedTags = [];

            this.formSubmitted = false; // Réinitialise l'état de soumission pour masquer les erreurs visuelles
            // Réinitialiser les classes d'erreur visuelles de tous les champs
            this.$root.querySelectorAll('.border-red-500').forEach(el => {
                el.classList.remove('border-red-500');
            });
            if (typeof showToast !== 'undefined') {
                showToast("Formulaire effacé !", 'info');
            }
        },

        /**
         * Définit la date du champ date.
         * @param {string} type - 'today' ou 'yesterday'.
         */
        setDate(type) {
            const dateObj = new Date();
            if (type === 'yesterday') {
                dateObj.setDate(dateObj.getDate() - 1);
            }
            this.date = dateObj.toISOString().slice(0, 10);
        },

        /**
         * Charge le dernier compte sélectionné depuis le localStorage.
         */
        loadLastAccount() {
            const lastSelectedAccountId = localStorage.getItem(LAST_ACCOUNT_KEY);
            if (lastSelectedAccountId) {
                const accountSelectElement = document.getElementById('id_account');
                if (accountSelectElement && Array.from(accountSelectElement.options).some(option => option.value === lastSelectedAccountId)) {
                    this.selectedAccount = lastSelectedAccountId;
                }
            }
        },

        /**
         * Sauvegarde le compte sélectionné dans le localStorage.
         */
        saveLastAccount() {
            localStorage.setItem(LAST_ACCOUNT_KEY, this.selectedAccount);
        },

        /**
         * Réinitialise la sous-catégorie quand la catégorie principale change.
         */
        updateSubcategoriesDropdown() {
            this.selectedSubcategory = ''; 
        },

        /**
         * Pas besoin de cette méthode pour les badges, x-html est réactif.
         */
        updateSubcategoryBadge() {
            // Cette méthode est appelée par le @change, mais ne fait plus d'opération DOM directe
            // car le x-html des badges est réactif à selectedSubcategory.
        },

        /**
         * Génère le HTML pour un badge.
         * @returns {string} HTML du badge.
         */
        createCategoryBadgeHtml(text, className) {
            return `<span class="category-info-icon ${className}">${text}</span>`;
        },

        /**
         * Génère le HTML pour les badges d'une catégorie.
         * @returns {string} HTML combiné des badges.
         */
        categoryBadgeHtml(category) {
            if (!category || !category.id) {
                return '';
            }
            let badgesHtml = '';
            if (category.is_fund_managed) {
                badgesHtml += this.createCategoryBadgeHtml('Fonds', 'fund-managed');
            }
            if (category.is_budgeted) {
                badgesHtml += this.createCategoryBadgeHtml('Budget', 'budgeted');
            }
            if (category.is_goal_linked) {
                badgesHtml += this.createCategoryBadgeHtml('Objectif', 'goal-linked');
            }
            return badgesHtml;
        },
        
        /**
         * Trouve une catégorie par son ID.
         * @returns {Object|null} L'objet catégorie ou null.
         */
        findCategoryById(categoryId, categoryList) {
            if (!categoryId || !categoryList) return null;
            return categoryList.find(cat => cat.id === parseInt(categoryId));
        },

        /**
         * Charge les descriptions courantes.
         */
        async loadCommonDescriptions() {
            try {
                const response = await fetch('/get-common-descriptions/');
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status} lors du chargement des descriptions courantes.`);
                }
                const data = await response.json();
                this.commonDescriptions = data;
            } catch (error) {
                console.error('Erreur lors du chargement des descriptions courantes:', error);
                if (typeof showToast !== 'undefined') {
                    showToast("Erreur lors du chargement des descriptions courantes.", 'error');
                }
            }
        },

        /**
         * Suggère une catégorisation via AJAX.
         */
        async suggestCategorization(description) {
            this.isLoadingSuggestion = true;
            try {
                const response = await fetch(`/suggest-categorization/?description=${encodeURIComponent(description)}`);
                if (!response.ok) {
                    throw new Error(`Erreur HTTP: ${response.status} lors de la suggestion de catégorisation.`);
                }
                const data = await response.json();

                if (data.category_id) {
                    this.selectedCategory = data.category_id.toString();
                    
                    this.$nextTick(() => { 
                        // S'assure que filteredSubcategories est à jour avant de vérifier la sous-catégorie
                        if (data.subcategory_id) {
                            if (this.filteredSubcategories.some(sub => sub.id === parseInt(data.subcategory_id))) {
                                this.selectedSubcategory = data.subcategory_id.toString();
                            } else {
                                this.selectedSubcategory = ''; 
                            }
                        } else {
                            this.selectedSubcategory = '';
                        }
                    });

                    if (data.tag_ids && Array.isArray(data.tag_ids)) {
                        this.selectedTags = data.tag_ids.map(id => parseInt(id));
                    } else {
                        this.selectedTags = [];
                    }

                    console.log('Suggestion appliquée:', data);
                } else {
                    console.log('Aucune suggestion trouvée pour la description.');
                }
            } catch (error) {
                console.error('Erreur lors de la suggestion de catégorisation:', error);
                if (typeof showToast !== 'undefined') {
                    showToast("Erreur lors de la suggestion de catégorisation.", 'error');
                }
            } finally {
                this.isLoadingSuggestion = false;
            }
        },

        /**
         * Valide le formulaire côté client.
         * @returns {boolean} True si valide.
         */
        validateForm(event) {
            this.formSubmitted = true; // Indique que le formulaire a été soumis
            let isValid = true;
            
            // Re-vérifie la validité des champs et applique/retire la classe d'erreur
            const fieldsToValidate = [
                { id: 'id_date', value: this.date, condition: !this.date, message: "La date est requise." },
                { id: 'id_description', value: this.description.trim(), condition: !this.description.trim(), message: "La description est requise." },
                { id: 'id_amount', value: this.amount, condition: (this.amount === null || isNaN(this.amount) || parseFloat(this.amount) <= 0), message: "Le montant doit être un nombre positif." },
                { id: 'id_category', value: this.selectedCategory, condition: !this.selectedCategory, message: "La catégorie principale est requise." },
                // La sous-catégorie est conditionnelle
                { id: 'id_subcategory', value: this.selectedSubcategory, condition: (this.hasSubcategoriesForSelectedCategory && !this.selectedSubcategory), message: "La sous-catégorie est requise pour cette catégorie principale." },
            ];

            fieldsToValidate.forEach(field => {
                const element = document.getElementById(field.id);
                if (field.condition) {
                    isValid = false;
                    element?.classList.add('border-red-500');
                    if (typeof showToast !== 'undefined') {
                        showToast(field.message, 'error');
                    }
                } else {
                    element?.classList.remove('border-red-500');
                }
            });

            return isValid;
        },
    };
}
