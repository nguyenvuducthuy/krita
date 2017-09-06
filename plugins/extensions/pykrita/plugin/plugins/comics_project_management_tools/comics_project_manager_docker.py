"""
Part of the comics project management tools (CPMT).

This is a docker that helps you organise your comics project.
"""
import sys
import json
import os
import zipfile  # quick reading of documents
import shutil
import xml.etree.ElementTree as ET
from PyQt5.QtCore import QElapsedTimer
from PyQt5.QtGui import QStandardItem, QStandardItemModel, QImage, QIcon, QPixmap
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QTableView, QToolButton, QMenu, QAction, QPushButton, QSpacerItem, QSizePolicy, QWidget, QAbstractItemView, QProgressDialog, QDialog, QFileDialog, QDialogButtonBox, qApp, QSplitter, QSlider
import math
from krita import *
from . import comics_metadata_dialog, comics_exporter, comics_export_dialog, comics_project_setup_wizard, comics_template_dialog, comics_project_settings_dialog, comics_project_page_viewer

"""
This is a Krita docker called 'Comics Manager'.

It allows people to create comics project files, load those files, add pages, remove pages, move pages, manage the metadata,
and finally export the result.

The logic behind this docker is that it is very easy to get lost in a comics project due to the massive amount of files.
By having a docker that gives the user quick access to the pages and also allows them to do all of the meta-stuff, like
meta data, but also reordering the pages, the chaos of managing the project should take up less time, and more time can be focussed on actual writing and drawing.
"""


class comics_project_manager_docker(DockWidget):
    setupDictionary = {}
    stringName = i18n("Comics Manager")
    projecturl = None

    def __init__(self):
        super().__init__()
        self.setWindowTitle(self.stringName)

        # Setup layout:
        base = QHBoxLayout()
        widget = QWidget()
        widget.setLayout(base)
        self.baseLayout = QSplitter()
        base.addWidget(self.baseLayout)
        self.setWidget(widget)
        self.buttonLayout = QVBoxLayout()
        buttonBox = QWidget()
        buttonBox.setLayout(self.buttonLayout)
        self.baseLayout.addWidget(buttonBox)

        # Comic page list and pages model
        self.comicPageList = QTableView()
        self.comicPageList.verticalHeader().setSectionsMovable(True)
        self.comicPageList.verticalHeader().setDragEnabled(True)
        self.comicPageList.verticalHeader().setDragDropMode(QAbstractItemView.InternalMove)
        self.comicPageList.setAcceptDrops(True)
        self.pagesModel = QStandardItemModel()
        self.comicPageList.doubleClicked.connect(self.slot_open_page)
        self.comicPageList.setIconSize(QSize(128, 128))
        # self.comicPageList.itemDelegate().closeEditor.connect(self.slot_write_description)
        self.pagesModel.layoutChanged.connect(self.slot_write_config)
        self.pagesModel.rowsInserted.connect(self.slot_write_config)
        self.pagesModel.rowsRemoved.connect(self.slot_write_config)
        self.comicPageList.verticalHeader().sectionMoved.connect(self.slot_write_config)
        self.comicPageList.setModel(self.pagesModel)
        pageBox = QWidget()
        pageBox.setLayout(QVBoxLayout())
        zoomSlider = QSlider(Qt.Horizontal, None)
        zoomSlider.setRange(1, 8)
        zoomSlider.setValue(4)
        zoomSlider.setTickInterval(1)
        zoomSlider.valueChanged.connect(self.slot_scale_thumbnails)
        pageBox.layout().addWidget(zoomSlider)
        pageBox.layout().addWidget(self.comicPageList)
        self.baseLayout.addWidget(pageBox)

        self.btn_project = QToolButton()
        self.btn_project.setPopupMode(QToolButton.MenuButtonPopup)
        self.btn_project.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        menu_project = QMenu()
        self.action_new_project = QAction(i18n("New Project"), None)
        self.action_new_project.triggered.connect(self.slot_new_project)
        self.action_load_project = QAction(i18n("Open Project"), None)
        self.action_load_project.triggered.connect(self.slot_open_config)
        menu_project.addAction(self.action_new_project)
        menu_project.addAction(self.action_load_project)
        self.btn_project.setMenu(menu_project)
        self.btn_project.setDefaultAction(self.action_load_project)
        self.buttonLayout.addWidget(self.btn_project)

        # Settings dropdown with actions for the different settings menus.
        self.btn_settings = QToolButton()
        self.btn_settings.setPopupMode(QToolButton.MenuButtonPopup)
        self.btn_settings.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.action_edit_project_settings = QAction(i18n("Project Settings"), None)
        self.action_edit_project_settings.triggered.connect(self.slot_edit_project_settings)
        self.action_edit_meta_data = QAction(i18n("Meta Data"), None)
        self.action_edit_meta_data.triggered.connect(self.slot_edit_meta_data)
        self.action_edit_export_settings = QAction(i18n("Export Settings"), None)
        self.action_edit_export_settings.triggered.connect(self.slot_edit_export_settings)
        menu_settings = QMenu()
        menu_settings.addAction(self.action_edit_project_settings)
        menu_settings.addAction(self.action_edit_meta_data)
        menu_settings.addAction(self.action_edit_export_settings)
        self.btn_settings.setDefaultAction(self.action_edit_project_settings)
        self.btn_settings.setMenu(menu_settings)
        self.buttonLayout.addWidget(self.btn_settings)
        self.btn_settings.setDisabled(True)

        # Add page drop down with different page actions.
        self.btn_add_page = QToolButton()
        self.btn_add_page.setPopupMode(QToolButton.MenuButtonPopup)
        self.btn_add_page.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.action_add_page = QAction(i18n("Add Page"), None)
        self.action_add_page.triggered.connect(self.slot_add_new_page_single)
        self.action_add_template = QAction(i18n("Add Page From Template"), None)
        self.action_add_template.triggered.connect(self.slot_add_new_page_from_template)
        self.action_add_existing = QAction(i18n("Add Existing Pages"), None)
        self.action_add_existing.triggered.connect(self.slot_add_page_from_url)
        self.action_remove_selected_page = QAction(i18n("Remove Page"), None)
        self.action_remove_selected_page.triggered.connect(self.slot_remove_selected_page)
        self.action_resize_all_pages = QAction(i18n("Batch Resize"), None)
        self.action_resize_all_pages.triggered.connect(self.slot_batch_resize)
        self.btn_add_page.setDefaultAction(self.action_add_page)
        self.action_show_page_viewer = QAction(i18n("View Page In Window"), None)
        self.action_show_page_viewer.triggered.connect(self.slot_show_page_viewer)
        self.action_scrape_authors = QAction(i18n("Scrape Author Info"), None)
        self.action_scrape_authors.setToolTip(i18n("Search for author information in documents and add it to the author list. This doesn't check for duplicates."))
        self.action_scrape_authors.triggered.connect(self.slot_scrape_author_list)
        actionList = []
        menu_page = QMenu()
        actionList.append(self.action_add_page)
        actionList.append(self.action_add_template)
        actionList.append(self.action_add_existing)
        actionList.append(self.action_remove_selected_page)
        actionList.append(self.action_resize_all_pages)
        actionList.append(self.action_show_page_viewer)
        actionList.append(self.action_scrape_authors)
        menu_page.addActions(actionList)
        self.btn_add_page.setMenu(menu_page)
        self.buttonLayout.addWidget(self.btn_add_page)
        self.btn_add_page.setDisabled(True)

        self.comicPageList.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.comicPageList.addActions(actionList)

        # Export button that... exports.
        self.btn_export = QPushButton(i18n("Export Comic"))
        self.btn_export.clicked.connect(self.slot_export)
        self.buttonLayout.addWidget(self.btn_export)
        self.btn_export.setDisabled(True)

        self.btn_project_url = QPushButton(i18n("Copy Location"))
        self.btn_project_url.setToolTip(i18n("Copies the path of the project to the clipboard. Useful for quickly copying to a file manager or the like."))
        self.btn_project_url.clicked.connect(self.slot_copy_project_url)
        self.btn_project_url.setDisabled(True)
        self.buttonLayout.addWidget(self.btn_project_url)

        self.page_viewer_dialog = comics_project_page_viewer.comics_project_page_viewer()

        Application.notifier().imageSaved.connect(self.slot_check_for_page_update)

        self.buttonLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))

    """
    Open the config file and load the json file into a dictionary.
    """

    def slot_open_config(self):
        self.path_to_config = QFileDialog.getOpenFileName(caption=i18n("Please select the json comic config file."), filter=str(i18n("json files") + "(*.json)"))[0]
        if os.path.exists(self.path_to_config) is True:
            configFile = open(self.path_to_config, "r", newline="", encoding="utf-16")
            self.setupDictionary = json.load(configFile)
            self.projecturl = os.path.dirname(str(self.path_to_config))
            configFile.close()
            self.load_config()
    """
    Further config loading.
    """

    def load_config(self):
        self.setWindowTitle(self.stringName + ": " + str(self.setupDictionary["projectName"]))
        self.fill_pages()
        self.btn_settings.setEnabled(True)
        self.btn_add_page.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.btn_project_url.setEnabled(True)

    """
    Fill the pages model with the pages from the pages list.
    """

    def fill_pages(self):
        self.loadingPages = True
        self.pagesModel.clear()
        self.pagesModel.setHorizontalHeaderLabels([i18n("Page"), i18n("Description")])
        pagesList = []
        if "pages" in self.setupDictionary.keys():
            pagesList = self.setupDictionary["pages"]
        progress = QProgressDialog()
        progress.setMinimum(0)
        progress.setMaximum(len(pagesList))
        progress.setWindowTitle(i18n("Loading pages..."))
        for url in pagesList:
            absurl = os.path.join(self.projecturl, url)
            if (os.path.exists(absurl)):
                #page = Application.openDocument(absurl)
                page = zipfile.ZipFile(absurl, "r")
                thumbnail = QImage.fromData(page.read("preview.png"))
                pageItem = QStandardItem()
                dataList = self.get_description_and_title(page.read("documentinfo.xml"))
                if (dataList[0].isspace() or len(dataList[0]) < 1):
                    dataList[0] = os.path.basename(url)
                pageItem.setText(dataList[0])
                pageItem.setDragEnabled(True)
                pageItem.setDropEnabled(False)
                pageItem.setEditable(False)
                pageItem.setIcon(QIcon(QPixmap.fromImage(thumbnail)))
                pageItem.setToolTip(url)
                page.close()
                description = QStandardItem()
                description.setText(dataList[1])
                description.setEditable(False)
                listItem = []
                listItem.append(pageItem)
                listItem.append(description)
                self.pagesModel.appendRow(listItem)
                self.comicPageList.resizeRowsToContents()
                self.comicPageList.resizeColumnToContents(0)
                self.comicPageList.setColumnWidth(1, 256)
                progress.setValue(progress.value() + 1)
        progress.setValue(len(pagesList))
        self.loadingPages = False
    """
    Function that is triggered by the zoomSlider
    Resizes the thumbnails.
    """
    def slot_scale_thumbnails(self, multiplier = 4):
        self.comicPageList.setIconSize(QSize(multiplier*32, multiplier*32))
        self.comicPageList.resizeRowsToContents()

    """
    Function that takes the documentinfo.xml and parses it for the title, subject and abstract tags,
    to get the title and description.
    
    @returns a stringlist with the name on 0 and the description on 1.
    """

    def get_description_and_title(self, string):
        xmlDoc = ET.fromstring(string)
        calligra = str("{http://www.calligra.org/DTD/document-info}")
        name = ""
        if ET.iselement(xmlDoc[0].find(calligra + 'title')):
            name = xmlDoc[0].find(calligra + 'title').text
            if name is None:
                name = " "
        desc = ""
        if ET.iselement(xmlDoc[0].find(calligra + 'subject')):
            desc = xmlDoc[0].find(calligra + 'subject').text
        if desc is None or desc.isspace() or len(desc) < 1:
            if ET.iselement(xmlDoc[0].find(calligra + 'abstract')):
                desc = str(xmlDoc[0].find(calligra + 'abstract').text)
                if desc.startswith("<![CDATA["):
                    desc = desc[len("<![CDATA["):]
                if desc.startswith("]]>"):
                    desc = desc[:-len("]]>")]
        return [name, desc]

    """
    Scrapes authors from the author data in the document info and puts them into the author list.
    Doesn't check for duplicates.
    """

    def slot_scrape_author_list(self):
        listOfAuthors = []
        if "authorList" in self.setupDictionary.keys():
            listOfAuthors = self.setupDictionary["authorList"]
        if "pages" in self.setupDictionary.keys():
            for relurl in self.setupDictionary["pages"]:
                absurl = os.path.join(self.projecturl, relurl)
                page = zipfile.ZipFile(absurl, "r")
                xmlDoc = ET.fromstring(page.read("documentinfo.xml"))
                calligra = str("{http://www.calligra.org/DTD/document-info}")
                authorelem = xmlDoc.find(calligra + 'author')
                author = {}
                if ET.iselement(authorelem.find(calligra + 'full-name')):
                    author["nickname"] = str(authorelem.find(calligra + 'full-name').text)
                if ET.iselement(authorelem.find(calligra + 'email')):
                    author["email"] = str(authorelem.find(calligra + 'email').text)
                if ET.iselement(authorelem.find(calligra + 'position')):
                    author["role"] = str(authorelem.find(calligra + 'position').text)
                listOfAuthors.append(author)
                page.close()
        self.setupDictionary["authorList"] = listOfAuthors

    """
    Edit the general project settings like the project name, concept, pages location, export location, template location, metadata
    """

    def slot_edit_project_settings(self):
        dialog = comics_project_settings_dialog.comics_project_details_editor(self.projecturl)
        dialog.setConfig(self.setupDictionary, self.projecturl)

        if dialog.exec_() == QDialog.Accepted:
            self.setupDictionary = dialog.getConfig(self.setupDictionary)
            self.slot_write_config()
            self.setWindowTitle(self.stringName + ": " + str(self.setupDictionary["projectName"]))

    """
    This allows users to select existing pages and add them to the pages list. The pages are currently not copied to the pages folder. Useful for existing projects.
    """

    def slot_add_page_from_url(self):
        # get the pages.
        urlList = QFileDialog.getOpenFileNames(caption=i18n("Which existing pages to add?"), directory=self.projecturl, filter=str(i18n("Krita files") + "(*.kra)"))[0]

        # get the existing pages list.
        pagesList = []
        if "pages" in self.setupDictionary.keys():
            pagesList = self.setupDictionary["pages"]

        # And add each url in the url list to the pages list and the model.
        for url in urlList:
            if self.projecturl not in urlList:
                newUrl = os.path.join(self.projecturl, self.setupDictionary["pagesLocation"], os.path.basename(url))
                shutil.move(url, newUrl)
                url = newUrl
            relative = os.path.relpath(url, self.projecturl)
            if url not in pagesList:
                page = zipfile.ZipFile(url, "r")
                thumbnail = QImage.fromData(page.read("preview.png"))
                dataList = self.get_description_and_title(page.read("documentinfo.xml"))
                if (dataList[0].isspace() or len(dataList[0]) < 1):
                    dataList[0] = os.path.basename(url)
                newPageItem = QStandardItem()
                newPageItem.setIcon(QIcon(QPixmap.fromImage(thumbnail)))
                newPageItem.setDragEnabled(True)
                newPageItem.setDropEnabled(False)
                newPageItem.setEditable(False)
                newPageItem.setText(dataList[0])
                newPageItem.setToolTip(relative)
                page.close()
                description = QStandardItem()
                description.setText(dataList[1])
                description.setEditable(False)
                listItem = []
                listItem.append(newPageItem)
                listItem.append(description)
                self.pagesModel.appendRow(listItem)
                self.comicPageList.resizeRowsToContents()
                self.comicPageList.resizeColumnToContents(0)

    """
    Remove the selected page from the list of pages. This does not remove it from disk(far too dangerous).
    """

    def slot_remove_selected_page(self):
        index = self.comicPageList.currentIndex()
        self.pagesModel.removeRow(index.row())

    """
    This function adds a new page from the default template. If there's no default template, or the file does not exist, it will 
    show the create/import template dialog. It will remember the selected item as the default template.
    """

    def slot_add_new_page_single(self):
        templateUrl = "templatepage"
        templateExists = False

        if "singlePageTemplate" in self.setupDictionary.keys():
            templateUrl = self.setupDictionary["singlePageTemplate"]
        if os.path.exists(os.path.join(self.projecturl, templateUrl)):
            templateExists = True

        if templateExists is False:
            if "templateLocation" not in self.setupDictionary.keys():
                self.setupDictionary["templateLocation"] = os.path.relpath(QFileDialog.getExistingDirectory(caption=i18n("Where are the templates located?"), options=QFileDialog.ShowDirsOnly), self.projecturl)

            templateDir = os.path.join(self.projecturl, self.setupDictionary["templateLocation"])
            template = comics_template_dialog.comics_template_dialog(templateDir)

            if template.exec_() == QDialog.Accepted:
                templateUrl = os.path.relpath(template.url(), self.projecturl)
                self.setupDictionary["singlePageTemplate"] = templateUrl
        if os.path.exists(os.path.join(self.projecturl, templateUrl)):
            self.add_new_page(templateUrl)

    """
    This function always asks for a template showing the new template window. This allows users to have multiple different
    templates created for back covers, spreads, other and have them accesible, while still having the convenience of a singular
    "add page" that adds a default.
    """

    def slot_add_new_page_from_template(self):
        if "templateLocation" not in self.setupDictionary.keys():
            self.setupDictionary["templateLocation"] = os.path.relpath(QFileDialog.getExistingDirectory(caption=i18n("Where are the templates located?"), options=QFileDialog.ShowDirsOnly), self.projecturl)

        templateDir = os.path.join(self.projecturl, self.setupDictionary["templateLocation"])
        template = comics_template_dialog.comics_template_dialog(templateDir)

        if template.exec_() == QDialog.Accepted:
            templateUrl = os.path.relpath(template.url(), self.projecturl)
            self.add_new_page(templateUrl)

    """
    This is the actual function that adds the template using the template url.
    It will attempt to name the new page projectName+number, and tries to get the first possible
    number that is not in the pages list. If such a file already exists it will only append the file.
    """

    def add_new_page(self, templateUrl):

        # check for page list and or location.
        pagesList = []
        if "pages" in self.setupDictionary.keys():
            pagesList = self.setupDictionary["pages"]
        if (str(self.setupDictionary["pagesLocation"]).isspace()):
            self.setupDictionary["pagesLocation"] = os.path.relpath(QFileDialog.getExistingDirectory(caption=i18n("Where should the pages go?"), options=QFileDialog.ShowDirsOnly), self.projecturl)

        # Search for the possible name.
        extraUnderscore = str()
        if str(self.setupDictionary["projectName"])[-1].isdigit():
            extraUnderscore = "_"
        pageName = str(self.setupDictionary["projectName"]) + extraUnderscore + str(format(len(pagesList), "03d"))
        url = os.path.join(str(self.setupDictionary["pagesLocation"]), pageName + ".kra")
        pageNumber = 0
        if (url in pagesList):
            while (url in pagesList):
                pageNumber += 1
                pageName = str(self.setupDictionary["projectName"]) + extraUnderscore + str(format(pageNumber, "03d"))
                url = os.path.join(str(self.setupDictionary["pagesLocation"]), pageName + ".kra")

        # open the page by opening the template and resaving it, or just opening it.
        absoluteUrl = os.path.join(self.projecturl, url)
        if (os.path.exists(absoluteUrl)):
            newPage = Application.openDocument(absoluteUrl)
        else:
            booltemplateExists = os.path.exists(os.path.join(self.projecturl, templateUrl))
            if booltemplateExists is False:
                templateUrl = os.path.relpath(QFileDialog.getOpenFileName(caption=i18n("Which image should be the basis the new page?"), directory=self.projecturl, filter=str(i18n("Krita files") + "(*.kra)"))[0], self.projecturl)
            newPage = Application.openDocument(os.path.join(self.projecturl, templateUrl))
            newPage.setFileName(absoluteUrl)
            newPage.setName(pageName)
            newPage.exportImage(absoluteUrl, InfoObject())

        # Get out the extra data for the standard item.
        newPageItem = QStandardItem()
        newPageItem.setIcon(QIcon(QPixmap.fromImage(newPage.thumbnail(100, 100))))
        newPageItem.setDragEnabled(True)
        newPageItem.setDropEnabled(False)
        newPageItem.setEditable(False)
        newPageItem.setText(pageName)
        newPageItem.setToolTip(url)

        # close page document.
        newPage.waitForDone()
        if newPage.isIdle():
            newPage.close()

        # add item to page.
        description = QStandardItem()
        description.setText(str(""))
        description.setEditable(False)
        listItem = []
        listItem.append(newPageItem)
        listItem.append(description)
        self.pagesModel.appendRow(listItem)
        self.comicPageList.resizeRowsToContents()
        self.comicPageList.resizeColumnToContents(0)

    """
    Write to the json configuratin file.
    This also checks the current state of the pages list.
    """

    def slot_write_config(self):

        # Don't load when the pages are still being loaded, otherwise we'll be overwriting our own pages list.
        if (self.loadingPages is False):
            print("CPMT: writing comic configuration...")

            # Generate a pages list from the pagesmodel.
            # Because we made the drag-and-drop use the tableview header, we need to first request the logicalIndex
            # for the visualIndex, and then request the items for the logical index in the pagesmodel.
            # After that, we rename the verticalheader to have the appropriate numbers it will have when reloading.
            pagesList = []
            listOfHeaderLabels = []
            for i in range(self.pagesModel.rowCount()):
                listOfHeaderLabels.append(str(i))
            for i in range(self.pagesModel.rowCount()):
                iLogical = self.comicPageList.verticalHeader().logicalIndex(i)
                index = self.pagesModel.index(iLogical, 0)
                if index.isValid() is False:
                    index = self.pagesModel.index(i, 0)
                url = str(self.pagesModel.data(index, role=Qt.ToolTipRole))
                if url not in pagesList:
                    pagesList.append(url)
                listOfHeaderLabels[iLogical] = str(i + 1)
            self.pagesModel.setVerticalHeaderLabels(listOfHeaderLabels)
            self.comicPageList.verticalHeader().update()
            self.setupDictionary["pages"] = pagesList

            # Save to our json file.
            configFile = open(self.path_to_config, "w", newline="", encoding="utf-16")
            json.dump(self.setupDictionary, configFile, indent=4, sort_keys=True, ensure_ascii=False)
            configFile.close()
            print("CPMT: done")

    """
    Open a page in the pagesmodel in Krita.
    """

    def slot_open_page(self, index):
        if index.column() is 0:
            # Get the absolute url from the relative one in the pages model.
            absoluteUrl = os.path.join(self.projecturl, str(self.pagesModel.data(index, role=Qt.ToolTipRole)))

            # Make sure the page exists.
            if os.path.exists(absoluteUrl):
                page = Application.openDocument(absoluteUrl)

                # Set the title to the filename if it was empty. It looks a bit neater.
                if page.name().isspace or len(page.name()) < 1:
                    page.setName(str(self.pagesModel.data(index, role=Qt.DisplayRole)))

                # Add views for the document so the user can use it.
                Application.activeWindow().addView(page)
                Application.setActiveDocument(page)
            else:
                print("CPMT: The page cannot be opened because the file doesn't exist:", absoluteUrl)

    """
    Call up the metadata editor dialog. Only when the dialog is "Accepted" will the metadata be saved.
    """

    def slot_edit_meta_data(self):
        dialog = comics_metadata_dialog.comic_meta_data_editor()

        dialog.setConfig(self.setupDictionary)
        if (dialog.exec_() == QDialog.Accepted):
            self.setupDictionary = dialog.getConfig(self.setupDictionary)
            self.slot_write_config()

    """
    An attempt at making the description editable from the comic pages list. It is currently not working because ZipFile
    has no overwrite mechanism, and I don't have the energy to write one yet.
    """

    def slot_write_description(self, index):

        for row in range(self.pagesModel.rowCount()):
            index = self.pagesModel.index(row, 1)
            indexUrl = self.pagesModel.index(row, 0)
            absoluteUrl = os.path.join(self.projecturl, str(self.pagesModel.data(indexUrl, role=Qt.ToolTipRole)))
            page = zipfile.ZipFile(absoluteUrl, "a")
            xmlDoc = ET.ElementTree()
            ET.register_namespace("", "http://www.calligra.org/DTD/document-info")
            location = os.path.join(self.projecturl, "documentinfo.xml")
            xmlDoc.parse(location)
            xmlroot = ET.fromstring(page.read("documentinfo.xml"))
            calligra = "{http://www.calligra.org/DTD/document-info}"
            aboutelem = xmlroot.find(calligra + 'about')
            if ET.iselement(aboutelem.find(calligra + 'subject')):
                desc = aboutelem.find(calligra + 'subject')
                desc.text = self.pagesModel.data(index, role=Qt.EditRole)
                xmlstring = ET.tostring(xmlroot, encoding='unicode', method='xml', short_empty_elements=False)
                page.writestr(zinfo_or_arcname="documentinfo.xml", data=xmlstring)
                for document in Application.documents():
                    if str(document.fileName()) == str(absoluteUrl):
                        document.setDocumentInfo(xmlstring)
            page.close()

    """
    Calls up the export settings dialog. Only when accepted will the configuration be written.
    """

    def slot_edit_export_settings(self):
        dialog = comics_export_dialog.comic_export_setting_dialog()
        dialog.setConfig(self.setupDictionary)

        if (dialog.exec_() == QDialog.Accepted):
            self.setupDictionary = dialog.getConfig(self.setupDictionary)
            self.slot_write_config()

    """
    Export the comic. Won't work without export settings set.
    """

    def slot_export(self):
        exporter = comics_exporter.comicsExporter()
        exporter.set_config(self.setupDictionary, self.projecturl)
        exportSuccess = exporter.export()
        if exportSuccess:
            print("CPMT: Export success! The files have been written to the export folder!")

    """
    Calls up the comics project setup wizard so users can create a new json file with the basic information.
    """

    def slot_new_project(self):
        setup = comics_project_setup_wizard.ComicsProjectSetupWizard()
        setup.showDialog()

    def slot_check_for_page_update(self, url):
        if "pages" in self.setupDictionary.keys():
            relUrl = os.path.relpath(url, self.projecturl)
            if relUrl in self.setupDictionary["pages"]:
                index = self.pagesModel.index(self.setupDictionary["pages"].index(relUrl), 0)
                index2 = self.pagesModel.index(index.row(), 1)
                if index.isValid():
                    pageItem = self.pagesModel.itemFromIndex(index)
                    page = zipfile.ZipFile(url, "r")
                    dataList = self.get_description_and_title(page.read("documentinfo.xml"))
                    if (dataList[0].isspace() or len(dataList[0]) < 1):
                        dataList[0] = os.path.basename(url)
                    thumbnail = QImage.fromData(page.read("preview.png"))
                    pageItem.setIcon(QIcon(QPixmap.fromImage(thumbnail)))
                    pageItem.setText(dataList[0])
                    self.pagesModel.setItem(index.row(), index.column(), pageItem)
                    self.pagesModel.setData(index2, str(dataList[1]), Qt.DisplayRole)

    """
    Resize all the pages in the pages list.
    It will show a dialog with the options for resizing. Then, it will try to pop up a progress dialog while resizing.
    The progress dialog shows the remaining time and pages.
    """

    def slot_batch_resize(self):
        dialog = QDialog()
        dialog.setWindowTitle(i18n("Risize all pages."))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        sizesBox = comics_export_dialog.comic_export_resize_widget("Scale", batch=True, fileType=False)
        exporterSizes = comics_exporter.sizesCalculator()
        dialog.setLayout(QVBoxLayout())
        dialog.layout().addWidget(sizesBox)
        dialog.layout().addWidget(buttons)

        if dialog.exec_() == QDialog.Accepted:
            progress = QProgressDialog(i18n("Resizing pages..."), str(), 0, len(self.setupDictionary["pages"]))
            progress.setWindowTitle(i18n("Resizing pages."))
            progress.setCancelButton(None)
            timer = QElapsedTimer()
            timer.start()
            config = {}
            config = sizesBox.get_config(config)
            for p in range(len(self.setupDictionary["pages"])):
                absoluteUrl = os.path.join(self.projecturl, self.setupDictionary["pages"][p])
                progress.setValue(p)
                timePassed = timer.elapsed()
                if (p > 0):
                    timeEstimated = (len(self.setupDictionary["pages"]) - p) * (timePassed / p)
                    passedString = str(int(timePassed / 60000)) + ":" + format(int(timePassed / 1000), "02d") + ":" + format(timePassed % 1000, "03d")
                    estimatedString = str(int(timeEstimated / 60000)) + ":" + format(int(timeEstimated / 1000), "02d") + ":" + format(int(timeEstimated % 1000), "03d")
                    progress.setLabelText(str(i18n("{pages} of {pagesTotal} done. \nTime passed: {passedString}:\n Estimated:{estimated}")).format(pages=p, pagesTotal=len(self.setupDictionary["pages"]), passedString=passedString, estimated=estimatedString))
                if os.path.exists(absoluteUrl):
                    doc = Application.openDocument(absoluteUrl)
                    listScales = exporterSizes.get_scale_from_resize_config(config["Scale"], [doc.width(), doc.height(), doc.resolution(), doc.resolution()])
                    doc.scaleImage(listScales[0], listScales[1], listScales[2], listScales[3], "bicubic")
                    doc.waitForDone()
                    doc.save()
                    doc.waitForDone()
                    doc.close()

    def slot_show_page_viewer(self):
        index = self.comicPageList.currentIndex()
        if index.column() is not 0:
            index = self.pagesModel.index(index.row(), 0)
        # Get the absolute url from the relative one in the pages model.
        absoluteUrl = os.path.join(self.projecturl, str(self.pagesModel.data(index, role=Qt.ToolTipRole)))

        # Make sure the page exists.
        if os.path.exists(absoluteUrl):
            page = zipfile.ZipFile(absoluteUrl, "r")
            image = QImage.fromData(page.read("mergedimage.png"))
            self.page_viewer_dialog.update_image(image)
            self.page_viewer_dialog.show()
            page.close()
    """
    Function to copy the current project location into the clipboard.
    This is useful for users because they'll be able to use that url to quickly
    move to the project location in outside applications.
    """

    def slot_copy_project_url(self):
        if self.projecturl is not None:
            clipboard = qApp.clipboard()
            clipboard.setText(str(self.projecturl))
    """
    This is required by the dockwidget class, otherwise unused.
    """

    def canvasChanged(self, canvas):
        pass


"""
Add docker to program
"""
Application.addDockWidgetFactory(DockWidgetFactory("comics_project_manager_docker", DockWidgetFactoryBase.DockRight, comics_project_manager_docker))