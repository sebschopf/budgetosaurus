// Mise à jour du composant Alpine.js avec les nouvelles classes de badges
document.addEventListener("alpine:init", () => {
  Alpine.data("transactionManager", () => ({
    // État du formulaire
    isFormOpen: false,
    isEditing: false,
    editingTransactionId: null,

    // Données du formulaire
    transactionData: {
      transaction_type: "expense",
      description: "",
      amount: "",
      category: "",
      subcategory: "",
      date: new Date().toISOString().slice(0, 10),
      time: new Date().toTimeString().slice(0, 5),
      account: "",
      tags: [],
    },

    // Données des catégories
    allCategories: [],
    allSubcategories: [],
    filteredSubcategories: [],

    // Initialisation
    init() {
      this.loadCategoriesData()
      this.setupEventListeners()
    },

    loadCategoriesData() {
      const categoriesScript = document.getElementById("allCategoriesData")
      const subcategoriesScript = document.getElementById("allSubcategoriesData")

      if (categoriesScript) {
        try {
          this.allCategories = JSON.parse(categoriesScript.textContent)
        } catch (e) {
          console.error("Erreur lors du parsing des catégories:", e)
          this.allCategories = []
        }
      }

      if (subcategoriesScript) {
        try {
          this.allSubcategories = JSON.parse(subcategoriesScript.textContent)
        } catch (e) {
          console.error("Erreur lors du parsing des sous-catégories:", e)
          this.allSubcategories = []
        }
      }
    },

    setupEventListeners() {
      window.addEventListener("open-edit-form", (event) => {
        this.openEditForm(event.detail.transactionId)
      })
    },

    // Gestion du formulaire
    openAddForm() {
      this.isEditing = false
      this.editingTransactionId = null
      this.resetForm()
      this.isFormOpen = true
    },

    openEditForm(transactionId) {
      this.isEditing = true
      this.editingTransactionId = transactionId
      this.loadTransactionData(transactionId)
      this.isFormOpen = true
    },

    closeForm() {
      this.isFormOpen = false
      this.resetForm()
    },

    resetForm() {
      this.transactionData = {
        transaction_type: "expense",
        description: "",
        amount: "",
        category: "",
        subcategory: "",
        date: new Date().toISOString().slice(0, 10),
        time: new Date().toTimeString().slice(0, 5),
        account: "",
        tags: [],
      }
      this.filteredSubcategories = []
    },

    // Gestion des catégories
    updateSubcategoriesDropdown() {
      if (this.transactionData.category) {
        this.filteredSubcategories = this.allSubcategories.filter((sub) => sub.parent == this.transactionData.category)
        if (
          this.transactionData.subcategory &&
          !this.filteredSubcategories.find((sub) => sub.id == this.transactionData.subcategory)
        ) {
          this.transactionData.subcategory = ""
        }
      } else {
        this.filteredSubcategories = []
        this.transactionData.subcategory = ""
      }
    },

    // Utilitaires
    findCategoryById(categoryId, categoriesList) {
      return categoriesList.find((cat) => cat.id == categoryId) || null
    },

    // Badges avec classes Tailwind uniquement
    categoryBadgeHtml(category) {
      if (!category) return ""

      const badges = []
      if (category.is_budgeted) {
        badges.push(
          '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"><i class="fas fa-chart-pie mr-1"></i>Budget</span>',
        )
      }
      if (category.is_fund_managed) {
        badges.push(
          '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"><i class="fas fa-piggy-bank mr-1"></i>Fonds</span>',
        )
      }
      if (category.is_goal_linked) {
        badges.push(
          '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800"><i class="fas fa-target mr-1"></i>Objectif</span>',
        )
      }

      return badges.join(" ")
    },

    // Soumission du formulaire
    async submitForm() {
      try {
        const formData = new FormData()
        const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value

        Object.keys(this.transactionData).forEach((key) => {
          if (key === "tags" && Array.isArray(this.transactionData[key])) {
            this.transactionData[key].forEach((tag) => {
              formData.append("tags", tag)
            })
          } else {
            formData.append(key, this.transactionData[key])
          }
        })

        // Déterminer la catégorie finale
        if (this.transactionData.subcategory) {
          formData.append("final_category", this.transactionData.subcategory)
        } else if (this.transactionData.category) {
          formData.append("final_category", this.transactionData.category)
        }

        const url = this.isEditing ? `/transactions/edit/${this.editingTransactionId}/` : "/transactions/add/"

        const response = await fetch(url, {
          method: "POST",
          body: formData,
          headers: {
            "X-CSRFToken": csrfToken,
            "X-Requested-With": "XMLHttpRequest",
          },
        })

        const result = await response.json()

        if (result.success) {
          this.closeForm()
          window.dispatchEvent(new CustomEvent("transaction-updated"))

          if (typeof showToast === "function") {
            showToast(result.message || "Transaction sauvegardée avec succès", "success")
          }
        } else {
          if (result.errors) {
            console.error("Erreurs de validation:", result.errors)
          }

          if (typeof showToast === "function") {
            showToast(result.message || "Erreur lors de la sauvegarde", "error")
          }
        }
      } catch (error) {
        console.error("Erreur lors de la soumission:", error)
        if (typeof showToast === "function") {
          showToast("Erreur de connexion", "error")
        }
      }
    },

    async loadTransactionData(transactionId) {
      try {
        const response = await fetch(`/transactions/get/${transactionId}/`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        })

        const data = await response.json()

        if (data.success) {
          this.transactionData = { ...this.transactionData, ...data.transaction }
          this.updateSubcategoriesDropdown()
        } else {
          console.error("Erreur lors du chargement de la transaction")
        }
      } catch (error) {
        console.error("Erreur lors du chargement:", error)
      }
    },
  }))
})
