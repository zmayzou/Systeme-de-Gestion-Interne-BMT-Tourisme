# Système de Gestion Interne – BMT Tourisme

## Présentation du projet

Ce projet consiste en la conception et le développement d'une application web de gestion interne destinée à **BMT Tourisme**, une agence spécialisée dans les services de voyage et de tourisme.

L'objectif principal est de centraliser les informations, simplifier les processus administratifs et améliorer la coordination entre les différents services de l'agence.

Ce projet a été réalisé dans le cadre du **Projet de Fin d'Année (PFA)** à l'École Marocaine des Sciences de l'Ingénieur (EMSI).

## Fonctionnalités principales

- **Gestion des utilisateurs :** authentification, comptes employés, rôles et permissions.
- **Gestion des clients :** ajout, modification, consultation et suivi des clients.
- **Gestion des dossiers :** création et suivi des dossiers touristiques.
- **Gestion des tâches :** attribution des tâches, priorités et suivi d'avancement.
- **Gestion des paiements :** suivi des avances, règlements et soldes.
- **Gestion des visas :** suivi des demandes et de leurs statuts.
- **Gestion de la billetterie :** gestion des réservations et billets.
- **Gestion des guides :** organisation et suivi des missions.
- **Notifications :** suivi des événements et informations importantes.
- **Tableau de bord :** vue d'ensemble des activités.
- **Rapports et statistiques :** consultation des indicateurs de gestion.

## Technologies utilisées

| Technologie | Utilisation |
|---|---|
| Python | Langage de programmation |
| Django | Framework backend |
| MySQL | Base de données |
| HTML5 | Structure des pages |
| CSS3 | Mise en forme |
| Bootstrap | Interface responsive |
| JavaScript | Interactions côté client |
| WAMP | Environnement local de développement |

## Architecture du projet

L'application repose sur l'architecture **MVT (Model – View – Template)** de Django et sur une organisation modulaire.

Principaux modules Django :

```text
ProjectBMT/
├── accounts/
├── agencies/
├── clients/
├── dossiers/
├── tasks/
├── payments/
├── visa/
├── ticketing/
├── guides/
├── notifications/
├── reports/
└── ProjectBMT/
```

Cette structure facilite la maintenance et l'évolution de l'application.

## Sécurité et gestion des accès

L'application intègre un système de contrôle d'accès selon les rôles et les responsabilités des employés.

Les autorisations permettent de limiter l'accès aux fonctionnalités et aux données selon le profil de chaque utilisateur.

Le système prend également en compte le périmètre des agences pour organiser l'accès aux informations.

## Installation locale

**Prérequis :** Python, MySQL et Git.

**1. Cloner le dépôt**

```bash
git clone https://github.com/VOTRE-USERNAME/Systeme-de-Gestion-Interne-BMT-Tourisme.git
cd Systeme-de-Gestion-Interne-BMT-Tourisme
```

**2. Créer un environnement virtuel**

```bash
python -m venv venv
```

Sous Windows :

```bash
venv\Scripts\activate
```

**3. Installer les dépendances**

```bash
pip install -r requirements.txt
```

**4. Configurer la base de données**

Créer une base de données MySQL et renseigner les paramètres de connexion dans la configuration Django.

**5. Appliquer les migrations**

```bash
python manage.py migrate
```

**6. Lancer le serveur**

```bash
python manage.py runserver
```

Accéder ensuite à l'application :

`http://127.0.0.1:8000/`

*Remarque : les commandes supposent que le fichier `manage.py` et le fichier `requirements.txt` sont disponibles dans le répertoire courant. La configuration MySQL doit être adaptée à l'environnement local.*

## Perspectives d'amélioration

- Déploiement de l'application en production.
- Développement d'une interface complète d'administration des agences.
- Exportation des rapports en PDF, Excel et CSV.
- Intégration de notifications par e-mail.
- Développement d'une interface mobile pour les guides.
- Intégration d'API avec des services externes.

## Auteur

**ZAKARIA M'AYZOU**  
Étudiant en Génie Informatique  
École Marocaine des Sciences de l'Ingénieur (EMSI)  
Année universitaire : 2025–2026

**Projet :** Conception et développement d'un système de gestion interne pour BMT Tourisme.
