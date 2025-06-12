document.addEventListener("alpine:init", () => {
  // Définit un composant Alpine nommé 'transactionManager'
  // Ce composant gère l'état et la logique de la modale d'ajout/édition de transaction,
  // ainsi que l'interaction avec les données de catégories.
  Alpine.data("transactionManager", () => ({
    // --- ÉTAT DU COMPOSANT ---
    // Ces variables définissent l'état actuel de la modale et des données du formulaire.
    isFormOpen: false, // Contrôle la visibilité de la modale (true = ouverte, false = fermée).
    isEditing: false, // Indique si la modale est en mode édition (true) ou ajout (false).

    // transactionData: Cet objet stocke les valeurs des champs du formulaire.
    // x-model dans le HTML va lier directement ces propriétés aux inputs.
    transactionData: {
      id: null, // ID de la transaction (null pour un ajout, l'ID réel pour une édition).
      date: new Date().toISOString().slice(0, 10), // Date actuelle par défaut (format YYYY-MM-DD).
      time: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }), // Heure actuelle par défaut (format HH:MM).
      description: "", // Description de la transaction.
      amount: "", // Montant de la transaction.
      category: "", // ID de la catégorie principale sélectionnée.
      subcategory: "", // ID de la sous-catégorie sélectionnée.
      account: "", // ID du compte sélectionné.
      transaction_type: "expense", // Type de transaction ('expense' ou 'income').
      tags: [], // Tableau d'IDs des tags sélectionnés pour la transaction.
    },
    formUrl: "/add_transaction_submit/", // URL vers laquelle le formulaire sera soumis (par défaut pour l'ajout).

    // Données des catégories et sous-catégories, chargées depuis le contexte Django.
    // Ces tableaux contiennent toutes les catégories/sous-catégories disponibles pour l'utilisateur.
    allCategories: [],
    allSubcategories: [],
    filteredSubcategories: [], // Contient les sous-catégories filtrées en fonction de la catégorie principale sélectionnée.

    // --- MÉTHODE D'INITIALISATION ---
    // La méthode `init()` est automatiquement appelée par Alpine.js lorsque le composant est monté dans le DOM.
    init() {
      // Tente de parser les données JSON des catégories et sous-catégories injectées dans le HTML par Django.
      try {
        const categoriesElement = document.getElementById("allCategoriesData")
        const subcategoriesElement = document.getElementById("allSubcategoriesData")

        if (categoriesElement) {
          this.allCategories = JSON.parse(categoriesElement.textContent)
        }
        if (subcategoriesElement) {
          this.allSubcategories = JSON.parse(subcategoriesElement.textContent)
        }

        console.log("Categories loaded:", this.allCategories.length)
        console.log("Subcategories loaded:", this.allSubcategories.length)

        // Si une catégorie est déjà sélectionnée (par exemple, après une soumission de formulaire invalide et rechargement de la page),
        // assure que les sous-catégories sont également correctement peuplées à l'initialisation.
        if (this.transactionData.category) {
          this.updateSubcategoriesDropdown(this.transactionData.subcategory)
        }
      } catch (e) {
        console.error("Erreur lors de l'analyse des données de catégorie :", e)
        this.allCategories = [] // Assure que les tableaux restent vides en cas d'erreur.
        this.allSubcategories = []
      }
    },

    // --- ACTIONS DU COMPOSANT ---
    // Ces fonctions sont appelées par les interactions de l'utilisateur ou par d'autres parties du code.

    // Ouvre le formulaire pour l'ajout d'une NOUVELLE transaction.
    openAddForm() {
      this.isFormOpen = true // Affiche la modale.
      this.isEditing = false // Définit le mode sur "ajout".
      this.formUrl = "/add_transaction_submit/" // Définit l'URL de soumission pour l'ajout.
      this.resetForm() // Réinitialise tous les champs du formulaire.
      // Utilise $nextTick pour s'assurer que le DOM est mis à jour avant de manipuler les éléments.
      this.$nextTick(() => {
        this.populateCategoryDropdown() // Peuple la liste déroulante des catégories principales.
        this.transactionData.category = "" // Assure que la catégorie est vide pour un nouvel ajout.
        this.transactionData.subcategory = "" // Assure que la sous-catégorie est vide.
        this.updateSubcategoriesDropdown() // Met à jour/masque la liste des sous-catégories.
        const descriptionField = document.getElementById("id_description")
        if (descriptionField) {
          descriptionField.focus() // Met le focus sur le champ description.
        }
      })
    },

    // Ouvre le formulaire pour l'ÉDITION d'une transaction existante.
    openEditForm(transactionId) {
      this.isEditing = true // Définit le mode sur "édition".
      this.formUrl = `/update-transaction-category/${transactionId}/` // Définit l'URL de soumission pour l'édition.

      // Effectue une requête Fetch (AJAX) pour récupérer les données de la transaction depuis le serveur.
      fetch(`/get_transaction_data/${transactionId}/`)
        .then((response) => response.json()) // Parse la réponse JSON.
        .then((data) => {
          // Met à jour les propriétés de `transactionData` avec les données reçues.
          this.transactionData.id = data.id
          const transactionDate = new Date(data.date)
          this.transactionData.date = transactionDate.toISOString().slice(0, 10)
          this.transactionData.time =
            data.time || transactionDate.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
          this.transactionData.description = data.description
          this.transactionData.amount = data.amount
          this.transactionData.category = data.category_id
          this.transactionData.subcategory = data.subcategory_id
          this.transactionData.account = data.account_id
          this.transactionData.transaction_type = data.transaction_type
          this.transactionData.tags = data.tags // Les tags devraient être un tableau d'IDs.

          // Peuple les listes déroulantes de catégories et sous-catégories avec les valeurs de la transaction éditée.
          this.$nextTick(() => {
            this.populateCategoryDropdown(this.transactionData.category)
            this.updateSubcategoriesDropdown(this.transactionData.subcategory)
            this.isFormOpen = true // Ouvre la modale une fois que toutes les données sont chargées et les listes peuplées.
          })
        })
        .catch((error) => {
          console.error("Erreur lors de la récupération des données de transaction :", error)
          if (typeof showToast !== "undefined") {
            showToast("Erreur de chargement des données.", "error") // Affiche un message d'erreur.
          }
        })
    },

    // Ferme la modale du formulaire.
    closeForm() {
      this.isFormOpen = false // Masque la modale.
      this.resetForm() // Réinitialise le formulaire pour la prochaine utilisation.
    },

    // Réinitialise toutes les données du formulaire à leurs valeurs par défaut.
    resetForm() {
      this.transactionData = {
        id: null,
        date: new Date().toISOString().slice(0, 10),
        time: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
        description: "",
        amount: "",
        category: "",
        subcategory: "",
        account: "",
        transaction_type: "expense",
        tags: [],
      }
      this.filteredSubcategories = [] // Vide la liste des sous-catégories filtrées.
    },

    // Gère la soumission du formulaire (appelée par @submit.prevent="submitForm").
    submitForm() {
      const formData = new FormData() // Crée un objet FormData pour construire les données à envoyer.
      // Récupère le jeton CSRF pour la sécurité Django.
      const csrftoken = document.querySelector("[name=csrfmiddlewaretoken]").value

      // Ajoute toutes les propriétés de `transactionData` à l'objet FormData.
      Object.entries(this.transactionData).forEach(([key, value]) => {
        // S'assure que les IDs de catégorie, sous-catégorie et compte sont envoyés comme des nombres ou des chaînes vides.
        if (key === "category" || key === "subcategory" || key === "account") {
          formData.append(key, value === "" ? "" : Number.parseInt(value))
        } else if (Array.isArray(value)) {
          // Gère les tableaux (comme les tags) en ajoutant chaque élément séparément.
          value.forEach((item) => formData.append(key, item))
        } else if (value !== null && value !== undefined) {
          // Ajoute les autres valeurs non nulles/indéfinies.
          formData.append(key, value)
        }
      })

      // Ajoute le champ 'final_category' qui indique à Django quelle est la catégorie sélectionnée finale (sous-catégorie si présente, sinon catégorie principale).
      if (this.transactionData.subcategory) {
        formData.append("final_category", this.transactionData.subcategory)
      } else if (this.transactionData.category) {
        formData.append("final_category", this.transactionData.category)
      }

      // Effectue une requête Fetch (AJAX) vers l'URL du formulaire.
      fetch(this.formUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrftoken, // Jeton CSRF pour la sécurité.
          "X-Requested-With": "XMLHttpRequest", // Indique à Django que c'est une requête AJAX.
        },
        body: new URLSearchParams(formData), // Encode les données du formulaire pour l'envoi.
      })
        .then((response) => response.json()) // Parse la réponse JSON du serveur.
        .then((data) => {
          if (data.success) {
            if (typeof showToast !== "undefined") {
              showToast(this.isEditing ? "Transaction mise à jour !" : "Transaction ajoutée !", "success") // Affiche un toast de succès.
            }
            this.closeForm() // Ferme le formulaire.
            this.$dispatch("transaction-updated") // Déclenche un événement global pour recharger la page.
          } else {
            // En cas d'erreurs de validation du formulaire côté serveur.
            let errorMessages = []
            if (data.errors) {
              for (const field in data.errors) {
                if (data.errors.hasOwnProperty(field)) {
                  errorMessages = errorMessages.concat(data.errors[field]) // Collecte tous les messages d'erreur.
                  // Potentiellement, vous pourriez aussi afficher les erreurs à côté des champs spécifiques ici.
                }
              }
            }
            if (typeof showToast !== "undefined") {
              showToast(errorMessages.join(", ") || "Veuillez corriger les erreurs.", "error") // Affiche les erreurs dans un toast.
            }

            // S'assure que les listes déroulantes de catégories sont correctement re-peuplées avec les valeurs soumises
            // si le formulaire est renvoyé avec des erreurs par Django.
            this.$nextTick(() => {
              this.populateCategoryDropdown(this.transactionData.category)
              this.updateSubcategoriesDropdown(this.transactionData.subcategory)
            })
          }
        })
        .catch((error) => {
          console.error("Erreur lors de la soumission du formulaire :", error)
          if (typeof showToast !== "undefined") {
            showToast("Une erreur inattendue est survenue.", "error") // Gère les erreurs réseau ou inattendues.
          }
        })
    },

    // --- FONCTIONS UTILITAIRES POUR LES CATÉGORIES ---

    // Peuple la liste déroulante des catégories principales (<select id="id_category">).
    populateCategoryDropdown(initialSelectedId = "") {
      const categorySelect = document.getElementById("id_category")
      if (!categorySelect) {
        console.warn("Élément id_category non trouvé")
        return // Quitte si l'élément n'est pas trouvé.
      }

      categorySelect.innerHTML = '<option value="">-- Sélectionner --</option>' // Vide les options existantes.
      this.allCategories.forEach((category) => {
        const option = document.createElement("option")
        option.value = category.id
        option.textContent = category.name
        categorySelect.appendChild(option) // Ajoute chaque catégorie comme option.
      })

      // Assure que la valeur du x-model est définie après que les options sont ajoutées.
      if (initialSelectedId) {
        this.transactionData.category = initialSelectedId
        categorySelect.value = initialSelectedId
      }
    },

    // Met à jour la liste déroulante des sous-catégories (<select id="id_subcategory">)
    // en fonction de la catégorie principale sélectionnée.
    updateSubcategoriesDropdown(initialSelectedId = "") {
      const selectedCategoryId = this.transactionData.category
      const subcategorySelect = document.getElementById("id_subcategory")
      const subcategoryContainer = document.getElementById("subcategory-container") // CORRECTION: utilise le bon ID

      if (!subcategorySelect) {
        console.warn("Élément id_subcategory non trouvé")
        return // Quitte si l'élément n'est pas trouvé.
      }

      console.log("Updating subcategories for category:", selectedCategoryId)

      subcategorySelect.innerHTML = '<option value="">-- Sélectionner --</option>' // Vide les options.
      this.filteredSubcategories = [] // Réinitialise la liste des sous-catégories filtrées.

      if (selectedCategoryId) {
        // Filtre les sous-catégories dont le parent correspond à l'ID de la catégorie principale sélectionnée.
        // parseInt(selectedCategoryId) est crucial car les IDs du DOM peuvent être des chaînes,
        // tandis que l'ID 'parent' dans les données JS est un nombre.
        this.filteredSubcategories = this.allSubcategories.filter(
          (sub) => sub.parent === Number.parseInt(selectedCategoryId),
        )

        console.log("Filtered subcategories:", this.filteredSubcategories)

        this.filteredSubcategories.forEach((sub) => {
          const option = document.createElement("option")
          option.value = sub.id
          option.textContent = sub.name
          subcategorySelect.appendChild(option) // Ajoute chaque sous-catégorie comme option.
        })
      }

      // Définit la sous-catégorie sélectionnée initialement.
      if (initialSelectedId) {
        this.transactionData.subcategory = initialSelectedId
        subcategorySelect.value = initialSelectedId
      } else {
        this.transactionData.subcategory = ""
      }

      // Gère la visibilité du conteneur du champ de sous-catégorie.
      // Si aucune sous-catégorie filtrée n'est trouvée, le champ est masqué.
      if (subcategoryContainer) {
        if (this.filteredSubcategories.length > 0) {
          subcategoryContainer.style.display = "block"
          subcategoryContainer.classList.remove("hidden")
          console.log("Showing subcategory container")
        } else {
          subcategoryContainer.style.display = "none"
          subcategoryContainer.classList.add("hidden")
          console.log("Hiding subcategory container")
        }
      } else {
        console.warn("Conteneur subcategory-container non trouvé")
      }
    },

    // Fonction d'aide pour trouver un objet catégorie/sous-catégorie par son ID dans une collection.
    findCategoryById(id, collection) {
      const numericId = Number.parseInt(id) // Convertit l'ID en nombre pour une comparaison fiable.
      if (isNaN(numericId)) return null // Retourne null si l'ID n'est pas un nombre valide.
      return collection.find((item) => item.id === numericId) // Trouve et retourne l'élément correspondant.
    },

    // Fonction d'aide pour générer le HTML des badges de catégorie (Fonds, Budget, Objectif).
    categoryBadgeHtml(category) {
      if (!category) return "" // Retourne vide si aucune catégorie n'est fournie.
      let badges = ""
      // Ajoute les badges pertinents avec des classes Tailwind pour le style.
      if (category.is_fund_managed) {
        badges += `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 mr-1">Fonds</span>`
      }
      if (category.is_budgeted) {
        badges += `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mr-1">Budget</span>`
      }
      if (category.is_goal_linked) {
        badges += `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 mr-1">Objectif</span>`
      }
      return badges
    },
  }))
})
