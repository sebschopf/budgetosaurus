// Script de débogage pour la modale d'édition de transaction
document.addEventListener("DOMContentLoaded", () => {
  console.log("Debug script loaded")

  // Vérifier si Alpine.js est chargé
  console.log("Alpine.js loaded:", typeof Alpine !== "undefined")

  // Vérifier si la fonction triggerEdit est disponible
  console.log("triggerEdit function available:", typeof triggerEdit === "function")

  // Vérifier si le composant transactionEditor est défini
  if (typeof Alpine !== "undefined") {
    Alpine.nextTick(() => {
      const hasTransactionEditor = !!document.querySelector('[x-data="transactionEditor"]')
      console.log("transactionEditor component found in DOM:", hasTransactionEditor)
    })
  }

  // Intercepter les requêtes fetch pour le débogage
  const originalFetch = window.fetch
  window.fetch = function (...args) {
    const url = args[0]
    if (typeof url === "string" && url.includes("/transactions/")) {
      console.log("Intercepted fetch request to:", url)
    }
    return originalFetch
      .apply(this, args)
      .then((response) => {
        if (typeof url === "string" && url.includes("/transactions/")) {
          console.log("Fetch response status:", response.status)
        }
        return response
      })
      .catch((error) => {
        if (typeof url === "string" && url.includes("/transactions/")) {
          console.error("Fetch error:", error)
        }
        throw error
      })
  }
})
