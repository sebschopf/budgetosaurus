// Gestionnaire Alpine.js pour l'édition des transactions
document.addEventListener("alpine:init", () => {
  Alpine.data("transactionEditor", () => ({
    // État initial
    isOpen: false,
    isLoading: false,
    formHtml: "",
    currentTransactionId: null,
    error: null,

    // Initialisation du composant
    init() {
      console.log("TransactionEditor component initialized")

      // Écouter l'événement d'ouverture du formulaire d'édition
      window.addEventListener("open-edit-form", (event) => {
        console.log("Received open-edit-form event:", event.detail)
        this.openEditForm(event.detail.transactionId)
      })
    },

    // Ouvrir le formulaire d'édition
    async openEditForm(transactionId) {
      console.log("Opening edit form for transaction:", transactionId)

      // Validation de l'ID de transaction
      if (!transactionId || isNaN(transactionId)) {
        console.error("ID de transaction invalide:", transactionId)
        this.showError("ID de transaction invalide")
        return
      }

      // Réinitialiser l'état
      this.currentTransactionId = transactionId
      this.error = null
      this.formHtml = ""
      this.isOpen = true
      this.isLoading = true

      try {
        // Construire l'URL de la requête (selon votre urls.py)
        const url = `/get-transaction-form/${transactionId}/`
        console.log("Fetching form from:", url)

        // Effectuer la requête AJAX
        const response = await fetch(url, {
          method: "GET",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            Accept: "application/json",
          },
          credentials: "same-origin",
        })

        console.log("Response status:", response.status)
        console.log("Response headers:", Object.fromEntries(response.headers.entries()))

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Transaction non trouvée")
          } else if (response.status === 403) {
            throw new Error("Accès non autorisé à cette transaction")
          } else {
            throw new Error(`Erreur HTTP ${response.status}: ${response.statusText}`)
          }
        }

        const contentType = response.headers.get("content-type")
        if (!contentType || !contentType.includes("application/json")) {
          throw new Error("Réponse invalide du serveur (pas JSON)")
        }

        const data = await response.json()
        console.log("Form data received:", data)

        if (data.success && data.form_html) {
          this.formHtml = data.form_html
          console.log("Form HTML set, length:", this.formHtml.length)

          // Attendre que Alpine mette à jour le DOM
          await this.$nextTick()
          console.log("DOM updated, initializing category handlers")

          // Initialiser les gestionnaires de catégories
          this.initializeCategoryHandlers()
        } else {
          throw new Error(data.error || "Aucun HTML de formulaire reçu dans la réponse")
        }
      } catch (error) {
        console.error("Erreur lors du chargement du formulaire:", error)
        this.showError(error.message)
      } finally {
        this.isLoading = false
        console.log("Loading finished, isLoading:", this.isLoading)
      }
    },

    // Afficher une erreur dans la modale
    showError(message) {
      this.error = message
      this.formHtml = `
        <div class="text-center p-8">
          <div class="text-red-600 mb-4">
            <i class="fas fa-exclamation-triangle text-4xl mb-2"></i>
            <p class="text-lg font-semibold">Erreur</p>
          </div>
          <p class="text-gray-700 mb-4">${message}</p>
          <button @click="closeForm()" class="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600">
            Fermer
          </button>
        </div>
      `
    },

    // Initialiser les gestionnaires de catégories
    initializeCategoryHandlers() {
      console.log("Initializing category handlers")

      // Attendre un peu pour que le DOM soit complètement rendu
      setTimeout(() => {
        const categorySelect = document.querySelector("#id_category")
        const subcategorySelect = document.querySelector("#id_subcategory")
        const subcategoryContainer = document.querySelector("#subcategory-container")

        console.log("Category select found:", !!categorySelect)
        console.log("Subcategory select found:", !!subcategorySelect)
        console.log("Subcategory container found:", !!subcategoryContainer)

        if (!categorySelect || !subcategorySelect) {
          console.warn("Éléments de catégorie non trouvés dans le DOM")
          return
        }

        // Récupérer les données des catégories
        const categoriesScript = document.querySelector("#allCategoriesData")
        const subcategoriesScript = document.querySelector("#allSubcategoriesData")

        console.log("Categories script found:", !!categoriesScript)
        console.log("Subcategories script found:", !!subcategoriesScript)

        if (!categoriesScript || !subcategoriesScript) {
          console.warn("Scripts de données des catégories non trouvés")
          return
        }

        let allCategories, allSubcategories
        try {
          allCategories = JSON.parse(categoriesScript.textContent || "[]")
          allSubcategories = JSON.parse(subcategoriesScript.textContent || "[]")
          console.log("Categories loaded:", allCategories.length)
          console.log("Subcategories loaded:", allSubcategories.length)

          // Vérifier si les données sont vides
          if (allCategories.length === 0) {
            console.warn("Aucune catégorie trouvée dans les données JSON")
            // Essayer de récupérer les catégories depuis le DOM
            this.extractCategoriesFromDOM(categorySelect, subcategorySelect)
          }
        } catch (e) {
          console.error("Erreur lors du parsing des données de catégories:", e)
          // Essayer de récupérer les catégories depuis le DOM
          this.extractCategoriesFromDOM(categorySelect, subcategorySelect)
          return
        }

        // Fonction pour mettre à jour les sous-catégories
        const updateSubcategories = (categoryId) => {
          console.log("Updating subcategories for category:", categoryId)

          // Vider les options existantes
          subcategorySelect.innerHTML = '<option value="">Sélectionner une sous-catégorie</option>'

          if (categoryId) {
            // Filtrer les sous-catégories
            const filteredSubcategories = allSubcategories.filter((sub) => sub.parent == categoryId)

            console.log("Filtered subcategories:", filteredSubcategories.length)

            // Ajouter les sous-catégories
            filteredSubcategories.forEach((subcategory) => {
              const option = document.createElement("option")
              option.value = subcategory.id
              option.textContent = subcategory.name
              subcategorySelect.appendChild(option)
            })

            // Afficher/masquer le conteneur
            if (filteredSubcategories.length > 0 && subcategoryContainer) {
              subcategoryContainer.style.display = "block"
            } else if (subcategoryContainer) {
              subcategoryContainer.style.display = "none"
            }
          } else if (subcategoryContainer) {
            subcategoryContainer.style.display = "none"
          }
        }

        // Gestionnaire pour le changement de catégorie
        categorySelect.addEventListener("change", (e) => {
          updateSubcategories(e.target.value)
        })

        // Initialiser si une catégorie est déjà sélectionnée
        if (categorySelect.value) {
          updateSubcategories(categorySelect.value)
        } else if (subcategoryContainer) {
          subcategoryContainer.style.display = "none"
        }

        console.log("Category handlers initialized successfully")
      }, 150) // Délai augmenté pour s'assurer que le DOM est prêt
    },

    // Extraire les catégories directement du DOM si les données JSON sont vides
    extractCategoriesFromDOM(categorySelect, subcategorySelect) {
      console.log("Extracting categories from DOM")

      // Créer un tableau de catégories à partir des options du select
      const allCategories = []
      const allSubcategories = []

      // Parcourir les options du select de catégories
      Array.from(categorySelect.options).forEach((option) => {
        if (option.value) {
          allCategories.push({
            id: option.value,
            name: option.textContent,
            is_fund_managed: false,
            is_budgeted: false,
          })
        }
      })

      console.log("Extracted categories from DOM:", allCategories.length)

      // Stocker les données dans des éléments script pour les utiliser plus tard
      const categoriesScript = document.createElement("script")
      categoriesScript.id = "allCategoriesData"
      categoriesScript.type = "application/json"
      categoriesScript.textContent = JSON.stringify(allCategories)

      const subcategoriesScript = document.createElement("script")
      subcategoriesScript.id = "allSubcategoriesData"
      subcategoriesScript.type = "application/json"
      subcategoriesScript.textContent = JSON.stringify(allSubcategories)

      // Ajouter les scripts au DOM
      document.body.appendChild(categoriesScript)
      document.body.appendChild(subcategoriesScript)
    },

    // Soumettre le formulaire
    async submitForm() {
      console.log("Submitting form for transaction:", this.currentTransactionId)

      const form = document.querySelector(".form-content form")
      if (!form) {
        console.error("Formulaire non trouvé dans le DOM")
        this.showError("Formulaire non trouvé")
        return
      }

      const formData = new FormData(form)

      try {
        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]")
        if (!csrfToken) {
          throw new Error("Token CSRF non trouvé")
        }

        // Utiliser l'URL correcte selon votre urls.py
        const response = await fetch(`/edit-transaction/${this.currentTransactionId}/`, {
          method: "POST",
          body: formData,
          headers: {
            "X-CSRFToken": csrfToken.value,
            "X-Requested-With": "XMLHttpRequest",
          },
          credentials: "same-origin",
        })

        const data = await response.json()
        console.log("Submit response:", data)

        if (data.success) {
          console.log("Formulaire soumis avec succès")
          this.closeForm()

          // Afficher un message de succès
          if (typeof showToast === "function") {
            showToast("Transaction mise à jour avec succès", "success")
          }

          // Recharger la page après un court délai
          setTimeout(() => {
            window.location.reload()
          }, 1000)
        } else {
          console.error("Échec de la soumission:", data)
          // Afficher les erreurs
          if (data.errors_html) {
            this.formHtml = data.errors_html
            await this.$nextTick()
            this.initializeCategoryHandlers()
          } else {
            this.showError(data.error || "Erreur lors de la soumission")
          }
        }
      } catch (error) {
        console.error("Erreur lors de la soumission:", error)
        this.showError("Erreur lors de la soumission du formulaire")
      }
    },

    // Fermer le formulaire
    closeForm() {
      console.log("Closing form")
      this.isOpen = false
      this.formHtml = ""
      this.currentTransactionId = null
      this.error = null
      this.isLoading = false
    },
  }))
})

// Fonction globale pour déclencher l'ouverture du formulaire
function triggerEdit(transactionId) {
  console.log("Triggering edit for transaction:", transactionId)

  // Vérifier que Alpine.js est chargé
  if (typeof Alpine === "undefined") {
    console.error("Alpine.js n'est pas chargé")
    alert("Erreur: Alpine.js n'est pas chargé")
    return
  }

  // Vérifier que l'ID est valide
  if (!transactionId || isNaN(transactionId)) {
    console.error("ID de transaction invalide:", transactionId)
    alert("Erreur: ID de transaction invalide")
    return
  }

  window.dispatchEvent(
    new CustomEvent("open-edit-form", {
      detail: { transactionId: Number.parseInt(transactionId) },
    }),
  )
}
