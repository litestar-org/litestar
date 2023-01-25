const baseURL = "https://starlite-api.github.io/starlite/"

const loadVersions = () => {
    return fetch(baseURL + "versions.json").then(res => res.json())
}


const getSelectedVersion = () => {
    if (!window.location.href.startsWith(baseURL)) {
        return null
    }
    const pathParts = window.location.href.replace(baseURL, "").split("/")
    if (pathParts.length === 0) {
        return null
    }
    return pathParts[0]
}


const createSelectedVersionEl = (currentVersion, latestVersion) => {
    const container = document.createElement("div")
    container.id = "selected-version"
    container.textContent = "Version: "

    const versionEl = document.createElement("span")
    versionEl.textContent = currentVersion === "latest" ? `${latestVersion} (latest)` : currentVersion
    container.appendChild(versionEl)

    return container
}

const makeVersionSelect = () => {
    const selectedVersion = getSelectedVersion()
    if (selectedVersion === null) {
        return
    }

    loadVersions().then(versions => {
        const searchBoxElement = document.getElementById("searchbox")
        const selectContainer = document.createElement("div")

        selectContainer.id = "version-select"

        const latestVersion = versions[0]["version"]
        const selectedVersionElement = createSelectedVersionEl(selectedVersion, latestVersion)
        selectContainer.appendChild(selectedVersionElement)

        const listElement = document.createElement("ul")
        listElement.classList.add("hidden")
        listElement.addEventListener("click", () => container.classList.toggle("hidden"))
        versions.forEach(version => {
            const listItem = document.createElement("li")
            const link = document.createElement("a")
            link.textContent = version.version === latestVersion ? version.title + " (latest)" : version.title
            link.href = baseURL + version.version
            listItem.appendChild(link)
            listElement.appendChild(listItem)

        })
        selectContainer.appendChild(listElement)

        searchBoxElement.after(selectContainer)
    })
}


window.addEventListener("DOMContentLoaded", makeVersionSelect)
