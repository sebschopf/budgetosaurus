// Composants Alpine.js pour la gestion des fonds
document.addEventListener("alpine:init", () => {
  // Composant pour le débit de fonds
  Alpine.data("fundDebitManager", () => ({
    // État
    originalAmount: 0,
    debitLines: [],
    totalDebited: 0,
    remainingAmount: 0,
    fundCategories: [],

    // Initialisation
    init() {
      this.loadInitialData()
      this.setupFormsetHandling()
      this.calculateRemaining()
    },

    loadInitialData() {
      // Charger le montant original
      const amountElement = document.getElementById("originalTransactionAmountData")
      if (amountElement) {
        this.originalAmount = Math.abs(Number.parseFloat(amountElement.textContent))
      }

      // Charger les catégories de fonds
      const categoriesElement = document.getElementById("fundManagedCategoriesData")
      if (categoriesElement) {
        try {
          this.fundCategories = JSON.parse(categoriesElement.textContent)
        } catch (e) {
          console.error("Erreur parsing catégories:", e)
          this.fundCategories = []
        }
      }

      // Charger les lignes existantes
      this.loadExistingLines()
    },

    loadExistingLines() {
      const existingLines = document.querySelectorAll(".debit-line")
      this.debitLines = Array.from(existingLines).map((line, index) => ({
        id: index,
        category: line.querySelector('select[name$="-category"]')?.value || "",
        amount: Number.parseFloat(line.querySelector('input[name$="-amount"]')?.value) || 0,
        notes: line.querySelector('input[name$="-notes"]')?.value || "",
        isDeleted: false,
        formIndex: index,
      }))
    },

    setupFormsetHandling() {
      // Mettre à jour les champs cachés du formset Django
      this.$watch(
        "debitLines",
        () => {
          this.updateFormsetFields()
          this.calculateRemaining()
        },
        { deep: true },
      )
    },

    // Actions
    addDebitLine() {
      const newIndex = this.getNextFormIndex()
      this.debitLines.push({
        id: Date.now(),
        category: "",
        amount: 0,
        notes: "",
        isDeleted: false,
        formIndex: newIndex,
      })
      this.updateTotalForms()
    },

    removeDebitLine(lineId) {
      const line = this.debitLines.find((l) => l.id === lineId)
      if (line) {
        line.isDeleted = true
      }
    },

    // Calculs
    calculateRemaining() {
      this.totalDebited = this.debitLines
        .filter((line) => !line.isDeleted)
        .reduce((sum, line) => sum + (Number.parseFloat(line.amount) || 0), 0)

      this.remainingAmount = this.originalAmount - this.totalDebited
    },

    // Validation
    validateForm() {
      const activeLines = this.debitLines.filter((line) => !line.isDeleted)

      if (activeLines.length === 0) {
        this.showError("Veuillez ajouter au moins une ligne de débit.")
        return false
      }

      for (const line of activeLines) {
        if (!line.category || !line.amount || line.amount <= 0) {
          this.showError("Veuillez remplir toutes les informations requises.")
          return false
        }
      }

      if (this.remainingAmount < -0.01) {
        this.showError("Le montant total débité dépasse le montant de la transaction.")
        return false
      }

      return true
    },

    // Soumission
    submitForm() {
      if (!this.validateForm()) return

      // Le formulaire Django se charge de la soumission
      document.getElementById("debitFundsForm").submit()
    },

    // Utilitaires
    getNextFormIndex() {
      const totalFormsInput = document.querySelector("#id_form-TOTAL_FORMS")
      return totalFormsInput ? Number.parseInt(totalFormsInput.value) : this.debitLines.length
    },

    updateTotalForms() {
      const totalFormsInput = document.querySelector("#id_form-TOTAL_FORMS")
      if (totalFormsInput) {
        totalFormsInput.value = this.debitLines.length
      }
    },

    updateFormsetFields() {
      // Synchroniser avec les champs du formset Django
      this.debitLines.forEach((line, index) => {
        const prefix = `form-${line.formIndex}`

        // Mettre à jour les champs
        this.updateField(`${prefix}-category`, line.category)
        this.updateField(`${prefix}-amount`, line.amount)
        this.updateField(`${prefix}-notes`, line.notes)
        this.updateField(`${prefix}-DELETE`, line.isDeleted)
      })
    },

    updateField(name, value) {
      const field = document.querySelector(`[name="${name}"]`)
      if (field) {
        if (field.type === "checkbox") {
          field.checked = value
        } else {
          field.value = value
        }
      }
    },

    getCategoryName(categoryId) {
      const category = this.fundCategories.find((c) => c.id == categoryId)
      return category ? category.name : ""
    },

    getCategoryBadges(categoryId) {
      const category = this.fundCategories.find((c) => c.id == categoryId)
      if (!category) return ""

      let badges = ""
      if (category.is_fund_managed) {
        badges +=
          '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 mr-1">Fonds</span>'
      }
      if (category.is_budgeted) {
        badges +=
          '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mr-1">Budget</span>'
      }
      return badges
    },

    showError(message) {
      if (typeof showToast === "function") {
        showToast(message, "error")
      } else {
        alert(message)
      }
    },

    // Getters pour les classes CSS
    get remainingClass() {
      if (Math.abs(this.remainingAmount) < 0.01) return "text-green-600"
      if (this.remainingAmount < 0) return "text-red-600"
      return "text-gray-600"
    },

    get isBalanced() {
      return Math.abs(this.remainingAmount) < 0.01
    },
  }))

  // Composant pour l'allocation de revenus
  Alpine.data("incomeAllocationManager", () => ({
    // État similaire au débit de fonds mais pour l'allocation
    originalAmount: 0,
    allocationLines: [],
    totalAllocated: 0,
    remainingAmount: 0,
    fundCategories: [],

    init() {
      this.loadInitialData()
      this.setupFormsetHandling()
      this.calculateRemaining()
    },

    loadInitialData() {
      const amountElement = document.getElementById("originalTransactionAmountData")
      if (amountElement) {
        this.originalAmount = Number.parseFloat(amountElement.textContent)
      }

      const categoriesElement = document.getElementById("fundManagedCategoriesData")
      if (categoriesElement) {
        try {
          this.fundCategories = JSON.parse(categoriesElement.textContent)
        } catch (e) {
          console.error("Erreur parsing catégories:", e)
          this.fundCategories = []
        }
      }

      this.loadExistingLines()
    },

    loadExistingLines() {
      const existingLines = document.querySelectorAll(".allocation-line")
      this.allocationLines = Array.from(existingLines).map((line, index) => ({
        id: index,
        category: line.querySelector('select[name$="-category"]')?.value || "",
        amount: Number.parseFloat(line.querySelector('input[name$="-amount"]')?.value) || 0,
        notes: line.querySelector('input[name$="-notes"]')?.value || "",
        isDeleted: false,
        formIndex: index,
      }))
    },

    setupFormsetHandling() {
      this.$watch(
        "allocationLines",
        () => {
          this.updateFormsetFields()
          this.calculateRemaining()
        },
        { deep: true },
      )
    },

    addAllocationLine() {
      const newIndex = this.getNextFormIndex()
      this.allocationLines.push({
        id: Date.now(),
        category: "",
        amount: 0,
        notes: "",
        isDeleted: false,
        formIndex: newIndex,
      })
      this.updateTotalForms()
    },

    removeAllocationLine(lineId) {
      const line = this.allocationLines.find((l) => l.id === lineId)
      if (line) {
        line.isDeleted = true
      }
    },

    calculateRemaining() {
      this.totalAllocated = this.allocationLines
        .filter((line) => !line.isDeleted)
        .reduce((sum, line) => sum + (Number.parseFloat(line.amount) || 0), 0)

      this.remainingAmount = this.originalAmount - this.totalAllocated
    },

    validateForm() {
      const activeLines = this.allocationLines.filter((line) => !line.isDeleted)

      if (activeLines.length === 0) {
        this.showError("Veuillez ajouter au moins une ligne d'allocation.")
        return false
      }

      for (const line of activeLines) {
        if (!line.category || !line.amount || line.amount <= 0) {
          this.showError("Veuillez remplir toutes les informations requises.")
          return false
        }
      }

      if (this.remainingAmount < -0.01) {
        this.showError("Le montant total alloué dépasse le montant de la transaction.")
        return false
      }

      return true
    },

    submitForm() {
      if (!this.validateForm()) return
      document.getElementById("allocationForm").submit()
    },

    getNextFormIndex() {
      const totalFormsInput = document.querySelector("#id_form-TOTAL_FORMS")
      return totalFormsInput ? Number.parseInt(totalFormsInput.value) : this.allocationLines.length
    },

    updateTotalForms() {
      const totalFormsInput = document.querySelector("#id_form-TOTAL_FORMS")
      if (totalFormsInput) {
        totalFormsInput.value = this.allocationLines.length
      }
    },

    updateFormsetFields() {
      this.allocationLines.forEach((line) => {
        const prefix = `form-${line.formIndex}`

        this.updateField(`${prefix}-category`, line.category)
        this.updateField(`${prefix}-amount`, line.amount)
        this.updateField(`${prefix}-notes`, line.notes)
        this.updateField(`${prefix}-DELETE`, line.isDeleted)
      })
    },

    updateField(name, value) {
      const field = document.querySelector(`[name="${name}"]`)
      if (field) {
        if (field.type === "checkbox") {
          field.checked = value
        } else {
          field.value = value
        }
      }
    },

    getCategoryName(categoryId) {
      const category = this.fundCategories.find((c) => c.id == categoryId)
      return category ? category.name : ""
    },

    showError(message) {
      if (typeof showToast === "function") {
        showToast(message, "error")
      } else {
        alert(message)
      }
    },

    get remainingClass() {
      if (Math.abs(this.remainingAmount) < 0.01) return "text-green-600"
      if (this.remainingAmount < 0) return "text-red-600"
      return "text-gray-600"
    },

    get isBalanced() {
      return Math.abs(this.remainingAmount) < 0.01
    },
  }))

  // Composant pour la division de transactions
  Alpine.data("transactionSplitManager", () => ({
    originalAmount: 0,
    originalDescription: "",
    splitLines: [],
    totalSplit: 0,
    remainingAmount: 0,
    allCategories: [],
    allSubcategories: [],

    init() {
      this.loadInitialData()
      this.setupFormsetHandling()
      this.calculateRemaining()
    },

    loadInitialData() {
      const amountElement = document.getElementById("originalTransactionAmountData")
      if (amountElement) {
        this.originalAmount = Math.abs(Number.parseFloat(amountElement.textContent))
      }

      // Charger la description originale
      const originalInfo = document.querySelector(".original-transaction-info")
      if (originalInfo) {
        const descElement = originalInfo.querySelector("p:nth-of-type(2)")
        if (descElement) {
          this.originalDescription = descElement.textContent.replace("Description: ", "").trim()
        }
      }

      // Charger les catégories
      try {
        const categoriesElement = document.getElementById("allCategoriesData")
        const subcategoriesElement = document.getElementById("allSubcategoriesData")

        if (categoriesElement) {
          this.allCategories = JSON.parse(categoriesElement.textContent)
        }
        if (subcategoriesElement) {
          this.allSubcategories = JSON.parse(subcategoriesElement.textContent)
        }
      } catch (e) {
        console.error("Erreur parsing catégories:", e)
      }

      this.loadExistingLines()
    },

    loadExistingLines() {
      const existingLines = document.querySelectorAll(".split-line")
      this.splitLines = Array.from(existingLines).map((line, index) => ({
        id: index,
        description: line.querySelector('input[name$="-description"]')?.value || "",
        amount: Number.parseFloat(line.querySelector('input[name$="-amount"]')?.value) || 0,
        mainCategory: line.querySelector('select[name$="-main_category"]')?.value || "",
        subcategory: line.querySelector('select[name$="-subcategory"]')?.value || "",
        isDeleted: false,
        formIndex: index,
      }))

      // Si aucune ligne existante, créer la première
      if (this.splitLines.length === 0) {
        this.addSplitLine()
      }
    },

    setupFormsetHandling() {
      this.$watch(
        "splitLines",
        () => {
          this.updateFormsetFields()
          this.calculateRemaining()
          this.autoAddLineIfNeeded()
        },
        { deep: true },
      )
    },

    addSplitLine() {
      const newIndex = this.getNextFormIndex()
      this.splitLines.push({
        id: Date.now(),
        description: this.originalDescription,
        amount: 0,
        mainCategory: "",
        subcategory: "",
        isDeleted: false,
        formIndex: newIndex,
      })
      this.updateTotalForms()
    },

    removeSplitLine(lineId) {
      const line = this.splitLines.find((l) => l.id === lineId)
      if (line) {
        line.isDeleted = true
      }
    },

    autoAddLineIfNeeded() {
      const activeLines = this.splitLines.filter((line) => !line.isDeleted)
      const lastLine = activeLines[activeLines.length - 1]

      if (lastLine && this.isLineComplete(lastLine) && this.remainingAmount > 0.01) {
        this.addSplitLine()
        // Pré-remplir le montant restant
        const newLine = this.splitLines[this.splitLines.length - 1]
        newLine.amount = this.remainingAmount
      }
    },

    isLineComplete(line) {
      return (
        line.description.trim() !== "" &&
        line.amount > 0 &&
        line.mainCategory !== "" &&
        (line.subcategory !== "" || !this.hasSubcategories(line.mainCategory))
      )
    },

    hasSubcategories(categoryId) {
      return this.allSubcategories.some((sub) => sub.parent == categoryId)
    },

    getSubcategories(categoryId) {
      return this.allSubcategories.filter((sub) => sub.parent == categoryId)
    },

    calculateRemaining() {
      this.totalSplit = this.splitLines
        .filter((line) => !line.isDeleted)
        .reduce((sum, line) => sum + (Number.parseFloat(line.amount) || 0), 0)

      this.remainingAmount = this.originalAmount - this.totalSplit
    },

    validateForm() {
      const activeLines = this.splitLines.filter((line) => !line.isDeleted)

      if (activeLines.length === 0) {
        this.showError("Veuillez ajouter au moins une ligne de division.")
        return false
      }

      for (const line of activeLines) {
        if (!this.isLineComplete(line)) {
          this.showError("Veuillez remplir toutes les informations requises.")
          return false
        }
      }

      if (Math.abs(this.remainingAmount) > 0.01) {
        this.showError("La somme des montants divisés ne correspond pas au montant original.")
        return false
      }

      return true
    },

    submitForm() {
      if (!this.validateForm()) return
      document.getElementById("splitTransactionForm").submit()
    },

    getNextFormIndex() {
      const totalFormsInput = document.querySelector("#id_split_lines-TOTAL_FORMS")
      return totalFormsInput ? Number.parseInt(totalFormsInput.value) : this.splitLines.length
    },

    updateTotalForms() {
      const totalFormsInput = document.querySelector("#id_split_lines-TOTAL_FORMS")
      if (totalFormsInput) {
        totalFormsInput.value = this.splitLines.length
      }
    },

    updateFormsetFields() {
      this.splitLines.forEach((line) => {
        const prefix = `split_lines-${line.formIndex}`

        this.updateField(`${prefix}-description`, line.description)
        this.updateField(`${prefix}-amount`, line.amount)
        this.updateField(`${prefix}-main_category`, line.mainCategory)
        this.updateField(`${prefix}-subcategory`, line.subcategory)
        this.updateField(`${prefix}-DELETE`, line.isDeleted)
      })
    },

    updateField(name, value) {
      const field = document.querySelector(`[name="${name}"]`)
      if (field) {
        if (field.type === "checkbox") {
          field.checked = value
        } else {
          field.value = value
        }
      }
    },

    getCategoryName(categoryId) {
      const category =
        this.allCategories.find((c) => c.id == categoryId) || this.allSubcategories.find((c) => c.id == categoryId)
      return category ? category.name : ""
    },

    showError(message) {
      if (typeof showToast === "function") {
        showToast(message, "error")
      } else {
        alert(message)
      }
    },

    get remainingClass() {
      if (Math.abs(this.remainingAmount) < 0.01) return "text-green-600"
      if (this.remainingAmount < 0) return "text-red-600"
      return "text-gray-600"
    },

    get isBalanced() {
      return Math.abs(this.remainingAmount) < 0.01
    },

    get canSubmit() {
      return this.isBalanced && this.splitLines.filter((line) => !line.isDeleted).length > 0
    },
  }))
})
