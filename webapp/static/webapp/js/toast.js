// Votre fichier toast.js reste identique - il fonctionne parfaitement en vanilla JS
// webapp/static/webapp/js/toast.js

document.addEventListener("DOMContentLoaded", () => {
  const toastContainer = document.createElement("div")
  toastContainer.classList.add("toast-container")
  document.body.appendChild(toastContainer)

  // Mappage des tags Django vers les classes et icônes
  const tagMap = {
    success: { class: "toast-success", icon: "&#10003;" }, // Coche
    error: { class: "toast-error", icon: "&#10060;" }, // Croix rouge
    info: { class: "toast-info", icon: "&#8505;" }, // Symbole information
    warning: { class: "toast-warning", icon: "&#9888;" }, // Symbole avertissement
  }

  // Tente de récupérer les messages depuis l'élément script masqué
  const messagesElement = document.getElementById("django-messages")
  let messages = []
  if (messagesElement && messagesElement.textContent) {
    try {
      messages = JSON.parse(messagesElement.textContent)
    } catch (e) {
      console.error("Erreur lors du parsing des messages Django:", e)
    }
  }

  messages.forEach((msg) => {
    showToast(msg.message, msg.tags)
  })

  /**
   * Affiche un message toast.
   * @param {string} message Le texte du message.
   * @param {string} tags Les tags Django (ex: 'success', 'error').
   * @param {number} duration La durée d'affichage en ms (par défaut 5000).
   */
  function showToast(message, tags, duration = 5000) {
    const toast = document.createElement("div")
    let toastClass = ""
    let toastIcon = ""

    // Déterminer la classe et l'icône basées sur les tags
    const messageTags = tags.split(" ")
    let foundTag = false
    for (const tag of messageTags) {
      if (tagMap[tag]) {
        toastClass = tagMap[tag].class
        toastIcon = tagMap[tag].icon
        foundTag = true
        break
      }
    }
    if (!foundTag) {
      toastClass = "toast-info"
      toastIcon = tagMap["info"].icon
    }

    toast.classList.add("toast", toastClass)
    toast.innerHTML = `
            <div class="toast-icon">${toastIcon}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close-btn">&times;</button>
        `

    toastContainer.appendChild(toast)

    // Positionnement initial pour l'animation d'apparition
    requestAnimationFrame(() => {
      toast.style.opacity = "1"
      toast.style.transform = "translateY(0)"
    })

    // Supprimer le toast après la durée spécifiée
    let hideTimeout = setTimeout(() => {
      dismissToast(toast)
    }, duration)

    // Gérer le clic sur le bouton de fermeture
    const closeButton = toast.querySelector(".toast-close-btn")
    closeButton.addEventListener("click", () => {
      clearTimeout(hideTimeout)
      dismissToast(toast)
    })

    // Empêcher le fadeOut si la souris est sur le toast
    toast.addEventListener("mouseover", () => {
      clearTimeout(hideTimeout)
      toast.style.animationPlayState = "paused"
    })

    // Reprendre le fadeOut si la souris quitte le toast
    toast.addEventListener("mouseleave", () => {
      toast.style.animationPlayState = "running"
      hideTimeout = setTimeout(() => {
        dismissToast(toast)
      }, 1000)
    })
  }

  /**
   * Lance l'animation de disparition et supprime le toast du DOM.
   * @param {HTMLElement} toastElement L'élément toast à masquer.
   */
  function dismissToast(toastElement) {
    toastElement.style.animation = "fadeOut 0.5s ease-out forwards"
    toastElement.addEventListener(
      "animationend",
      () => {
        toastElement.remove()
      },
      { once: true },
    )
  }

  // Rendre showToast disponible globalement
  window.showToast = showToast
})
