/*
 *  Copyright (c) 2014 Victor Lafon metabolic.ewilan@hotmail.fr
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public License
 * along with this library; see the file COPYING.LIB.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA 02110-1301, USA.
 */

#ifndef KORESOURCEBUNDLE_H
#define KORESOURCEBUNDLE_H

#include <QSet>
#include <QList>

#include <KoXmlWriter.h>

#include <KoResource.h>
#include "KoResourceBundleManifest.h"

#include "kritaresources_export.h"

class KoStore;

/**
 * @brief A KoResourceBundle is a zip file that contains resources,
 * some metadata about the creator of the bundle and a manifest file
 * that lists the contained resources.
 */
class KRITARESOURCES_EXPORT KoResourceBundle : public KoResource
{

public:
    /**
     * @brief ResourceBundle : Ctor * @param bundlePath the path of the bundle
     */
    KoResourceBundle(QString const& fileName);

    /**
     * @brief ~ResourceBundle : Dtor
     */
    ~KoResourceBundle() override;

    /**
     * @brief defaultFileExtension
     * @return the default file extension which should be when saving the resource
     */
    QString defaultFileExtension() const override;

    /**
     * @brief load : Load this resource.
     * @return true if succeed, false otherwise.
     */
    bool load() override;
    bool loadFromDevice(QIODevice *dev) override;

    /**
     * @brief save : Save this resource.
     * @return true if succeed, false otherwise.
     */
    bool save() override;

    bool saveToDevice(QIODevice* dev) const override;

    /**
     * @brief install : Install the contents of the resource bundle.
     */
    bool install();

    /**
     * @brief uninstall : Uninstall the resource bundle.
     */
    bool uninstall();

    /**
     * @brief addMeta : Add a Metadata to the resource
     * @param type type of the metadata
     * @param value value of the metadata
     */
    void setMetaData(const QString &key, const QString &value);
    const QString metaData(const QString &key, const QString &defaultValue = QString()) const;

    /**
     * @brief addFile : Add a file to the bundle
     * @param fileType type of the resource file
     * @param filePath path of the resource file
     */
    void addResource(QString fileType, QString filePath, QStringList fileTagList, const QByteArray md5sum);

    QList<QString> getTagsList();

    /**
     * @brief isInstalled
     * @return true if the bundle is installed, false otherwise.
     */
    bool isInstalled();
    /**
     * @brief setInstalled
     * This allows you to set installed or uninstalled upon loading. This is used with blacklists.
     */
    void setInstalled(bool install);

    void setThumbnail(QString);

    /**
     * @brief saveMetadata: saves bundle metadata
     * @param store bundle where to save the metadata
     */
    void saveMetadata(QScopedPointer<KoStore> &store);

    /**
     * @brief saveManifest: saves bundle manifest
     * @param store bundle where to save the manifest
     */
    void saveManifest(QScopedPointer<KoStore> &store);

    QStringList resourceTypes() const;
    QList<KoResource*> resources(const QString &resType = QString()) const;
    int resourceCount() const;
private:

    void writeMeta(const QString &metaTag, KoXmlWriter *writer);
    void writeUserDefinedMeta(const QString &metaTag, KoXmlWriter *writer);
    bool readMetaData(KoStore *resourceStore);

private:
    QImage m_thumbnail;
    KoResourceBundleManifest m_manifest;
    QMap<QString, QString> m_metadata;
    QSet<QString> m_bundletags;
    bool m_installed;
    QList<QByteArray> m_gradientsMd5Installed;
    QList<QByteArray> m_patternsMd5Installed;
    QList<QByteArray> m_brushesMd5Installed;
    QList<QByteArray> m_palettesMd5Installed;
    QList<QByteArray> m_workspacesMd5Installed;
    QList<QByteArray> m_presetsMd5Installed;
    QString m_bundleVersion;

};

#endif // KORESOURCEBUNDLE_H