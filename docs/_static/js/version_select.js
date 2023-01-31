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


const getLatestVersion = (versions) => {
    for (const version of versions) {
        if (version["aliases"].includes("latest")) {
            return version["version"]
        }
    }
    return "latest"
}


const createSelectedVersionEl = ({selectedVersion, latestVersion}) => {
    const container = document.createElement("div")
    container.id = "selected-version"
    container.textContent = "Version: "

    const versionEl = document.createElement("span")
    versionEl.textContent = selectedVersion === latestVersion ? `${latestVersion} (latest)` : selectedVersion
    container.appendChild(versionEl)

    return container
}


const addVersionBanner = ({selectedVersion, latestVersion}) => {
    if (selectedVersion === latestVersion) {
        return
    }
    const page = document.querySelector(".page")
    if (!page) {
        return
    }

    const container = document.createElement("div")
    container.id = "version-warning"
    const versionAdjective = selectedVersion === "dev" ? "a preview" : "an older"

    const versionText = document.createElement("span")
    versionText.textContent = `You are viewing the documentation for ${versionAdjective} version of Starlite.`

    const latestLink = document.createElement("a")
    latestLink.href = baseURL + "latest"
    latestLink.textContent = "Click here to get to the latest version"

    container.appendChild(versionText)
    container.appendChild(latestLink)

    page.parentElement.insertBefore(container, page)
}

const addVersionSelect = ({versions, selectedVersion, latestVersion}) => {
    const searchBoxElement = document.getElementById("searchbox")
    const selectContainer = document.createElement("div")

    selectContainer.id = "version-select"

    const selectedVersionElement = createSelectedVersionEl({selectedVersion, latestVersion})
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
}


window.addEventListener("DOMContentLoaded", () => {
    const selectedVersion = getSelectedVersion()
    if (selectedVersion === null) {
        return
    }

    loadVersions().then(versions => {
        const latestVersion = getLatestVersion(versions)
        const versionSpec = {versions, selectedVersion, latestVersion}

        addVersionSelect(versionSpec)
        addVersionBanner(versionSpec)
    })
})
