/*
 * Copyright (c) 2018 boud <boud@valdyas.org>
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 */
#ifndef KISNEWSWIDGET_H
#define KISNEWSWIDGET_H

#include <QWidget>
#include <QListView>

#include <ui_KisNewsPage.h>

class MultiFeedRssModel;

/**
 * @brief The KisNewsWidget class shows the latest news from Krita.org
 */
class KisNewsWidget : public QWidget, public Ui::KisNewsPage
{
    Q_OBJECT
public:
    explicit KisNewsWidget(QWidget *parent = nullptr);
private Q_SLOTS:
    void toggleNews(bool toggle);
    void itemSelected(const QModelIndex &idx);
private:
    bool m_getNews {false};
    MultiFeedRssModel *m_rssModel {0};
};

#endif // KISNEWSWIDGET_H
