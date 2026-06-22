<div align="center">
  <img src="togglenix-logo.png" alt="Logo Togglenix" width="160">
</div>

**[English version](README.md)** | Version française

# Togglenix

Application GTK4/Python pour activer/désactiver des modules d'une config
NixOS sans éditer les fichiers `.nix` à la main : une liste de modules
avec des switches, un scanner automatique basé sur la structure de mon repos 
https://github.com/Jeepyto/NixOS-Config qui retrouve tes modules
existants, le scan peut ne pas fonctionner si la structure est differente de la repos
de ce fait il y a aussi la possibilité d'aller rentré manuellement les modules a désactiver
puis un bouton "Appliquer" qui ouvre un terminal et lance un
rebuild du système.

Togglenix est un dépôt **autonome**. Il ne fait pas partie de
`NixOS-Config` — il s'installe à côté.

## Installation

Pas besoin de toucher à ton `flake.nix` ni à
`environment.systemPackages`. Ça installe Togglenix directement dans
ton `$HOME` :

```bash
curl -fsSL https://raw.githubusercontent.com/Jeepyto/Togglenix/main/install.sh | bash
```
Pour mettre à jour plus tard, relance simplement la même commande.

Ça construit une seule fois un environnement Python/GTK4 autonome (via
`nix-build`), puis installe :
- le code source dans `~/.local/share/togglenix/`
- un script de lancement `togglenix` dans `~/.local/bin/`
- une entrée de menu dans `~/.local/share/applications/togglenix.desktop`

Une fois terminé, tape `~/.local/bin/togglenix` dans un terminal ou 
clique sur son icône dans le menu d'applications. Une déconnexion/reconnexion de
session (ou un `gtk-update-icon-cache`) peut être nécessaire pour que
l'icône apparaisse.

Pour désinstaller :

```bash
rm -rf ~/.local/share/togglenix ~/.local/bin/togglenix ~/.local/share/applications/togglenix.desktop
```

> ⚠️ Cette méthode nécessite que Nix soit disponible (vrai sur NixOS
> par définition, ou sur toute distro avec Nix installé). Elle
> fonctionne telle quelle sur
> [GLF OS](https://framagit.org/gaming-linux-fr/glf-os/glf-os) aussi.

## Si ta config vit dans /etc/nixos (appartenant à root)

Sur une installation NixOS classique, `/etc/nixos` appartient à
`root` — Togglenix peut donc lire tes fichiers `.nix`, mais pas y
écrire directement avec tes droits utilisateur normaux. Quand ça
arrive, Togglenix retente automatiquement l'écriture via `pkexec` — tu
verras une demande de mot de passe système la première fois que tu
toggles un module, exactement comme pour le bouton "Appliquer". Si ton
repo vit plutôt dans ton propre `$HOME`, aucune demande n'est
nécessaire.

## Premier lancement : créer ta liste de modules

Togglenix démarre à vide tant que `~/.config/togglenix/modules.json`
n'existe pas. Deux façons de le remplir :

**Option A — scan automatique (recommandée)**
Ouvre **Préférences** (icône engrenage, en haut à droite) → règle
`root_path` vers ton repo NixOS → **Scanner mon repo**. Togglenix
parcourt ton repo à la recherche de `.nix`, suit les chaînes
d'imports, et t'affiche une liste plate des vrais modules trouvés (en
ignorant au passage les dossiers purement système — voir
« Comment le scanner décide quoi afficher » plus bas). Coche ceux qui
t'intéressent, clique sur **Importer la sélection**, et ils sont
ajoutés à ta liste — rien n'est modifié avant ta confirmation.

**Option B — ajouter les modules à la main**
Clique sur le bouton **+** en haut de la fenêtre :
- **Nom affiché** : ce que tu veux voir dans la liste (ex: "firefox")
- **Catégorie** : pour grouper l'affichage (ex: "navigateur")
- **Fichier default.nix** : chemin **complet**, relatif à la racine de
  ton repo, vers le fichier qui contient le bloc `imports = [ ... ];`
  concerné — attention, ça doit être le fichier lui-même, pas juste le
  dossier qui le contient
- **Chemin importé** : la ligne exacte telle qu'elle apparaît dans ce
  bloc `imports` (ex: `./firefox`)

**Si rien ne correspond et que tu veux repartir de zéro** : ouvre
Togglenix → Préférences → **Reset JSON** → confirme. La liste se vide,
`root_path` est conservé, et tu reconstruis manuellement à partir de zéro.

## Une précision sur la structure des modules sur GLF OS (et distros similaires)

Sur certaines distros (GLF OS par exemple), les paquets sont
généralement listés directement dans `environment.systemPackages`,
comme `pkgs.discord`, plutôt que via un bloc `imports = [ ./discord ]`
pointant vers un module séparé (c'est ainsi qu'est structuré le repo
`NixOS-Config` de l'auteur).

Bonne nouvelle : Togglenix gère déjà les deux styles sans aucune
modification. Le champ « Chemin importé » n'a pas besoin de commencer
par `./` — il doit juste correspondre exactement à une ligne de ton
fichier. Tu peux donc ajouter un module avec **Chemin importé** réglé
sur `pkgs.discord` ou `discord` (au lieu de `./discord`), et Togglenix commentera/
décommentera cette ligne exacte :

```nix
environment.systemPackages = [
  pkgs.vmware-workstation
  pkgs.realvnc-vnc-viewer
  pkgs.discord     # devient #pkgs.discord une fois désactivé
  pkgs.blender
];
```

## Comment ça marche (sous le capot)

Togglenix active ou désactive un module en commentant/décommentant sa
ligne dans un bloc `imports = [ ... ];` (ou une liste de paquets
`pkgs.xxx` / `with pkgs; [ ... ]` — voir la note plus haut).

Exemple : si `modules/nixos/navigateur/default.nix` contient :
```nix
imports = [
  ./firefox
  ./vivaldi
  ./brave
];
```
Togglenix peut désactiver firefox en transformant la ligne en
`#./firefox`, et la réactiver en l'inverse.

Togglenix édite directement le fichier `.nix` concerné, sans créer de
copie de sauvegarde — pense à back-up ton repo si tu veux
pouvoir revenir en arrière sur une modification.

### Comment le scanner décide quoi afficher

Beaucoup de configs NixOS imbriquent les imports sur plusieurs niveaux
juste pour s'organiser (ex: `modules` → `nixos` → `environnement` →
`dev` → `realvnc`). Le scanner est conçu pour sauter tout ça et
n'afficher que les modules que tu voudrais vraiment toggler :

- Un `default.nix` est traité comme un relais organisationnel
  transparent dès que TOUTES ses entrées sont des imports `./xxx`
  pointant vers d'autres fichiers scannés — peu importe la profondeur
  de la chaîne, aucun de ces dossiers-relais n'est jamais affiché.
- Le module réellement affiché est le DERNIER `./xxx` de la chaîne
  avant d'atteindre un fichier avec du vrai contenu (paquets, noms nus
  dans un bloc `with pkgs; [ ... ]`, etc.). Sa catégorie est le dossier
  du relais juste au-dessus de lui, ce qu'on appelle son parent.
- Certains noms de dossiers sont toujours complètement ignorés —
  `system`, `services`, `utilities`, `configuration`, `settings`,
  `game-performance`, `packages` — car ce sont typiquement des réglages
  système bas niveau plutôt que des applications à toggler. Modifie
  `_SCAN_SYSTEM_DIR_NAMES` dans `core.py` si ton propre repo utilise
  d'autres noms pour ce genre de dossier.
- `gnome` est un cas particulier : plutôt que d'afficher une seule
  ligne « gnome », le scanner liste individuellement chaque paquet
  trouvé à l'intérieur (catégorie réglée sur « gnome »), pour pouvoir
  les toggler un par un. (cas exclusif, le scan affiche l'enfant au 
  lieu du parent encore une fois, c'est prévu par rapport à la structure 
  du repo de l'auteur).
- `environment.gnome.excludePackages` est géré avec une logique
  inversée : un paquet listé là-dedans et NON commenté est en réalité
  **désinstallé** (Togglenix l'affiche donc comme désactivé) ; le toggler ON
  commente la ligne, pour pouvoir le réinstaller au rebuild..

## Les onglets Catégories, Modules et Modification

La fenêtre principale a un sélecteur de vues en haut, dans cet ordre :

- **Catégories** — un switch par catégorie. ON si au moins un module de
  la catégorie est actif, OFF seulement si tous sont inactifs. 
  Ce switch applique le même état à **tous** les modules de la
  catégorie en une fois (écrit réellement dans chaque fichier `.nix`
  concerné).
- **Modules** — la vue détaillée, un switch par module individuel.
- **Modification** — la même liste, mais avec des boutons crayon
  (modifier nom/catégorie/fichier/chemin) et corbeille (supprimer ce
  module précis, avec confirmation) sur chaque ligne. Pour repartir
  d'une liste entièrement vide d'un coup, utilise plutôt **Reset JSON**
  dans Préférences.

## Thème clair/sombre et langue

Togglenix suit le thème et la langue du système par défaut.

- Le bouton soleil/lune dans la barre d'en-tête force manuellement le
  thème clair ou sombre ; ce choix est sauvegardé et reste actif aux
  lancements suivants.
- Le bouton FR/EN fait pareil pour la langue de l'interface — il
  affiche la langue vers laquelle tu basculerais (donc "EN" quand
  l'appli est en français). Sauvegardé aussi entre les lancements.

## Le bouton "Appliquer"

Il ouvre un terminal système (essaie dans l'ordre : `kgx`/GNOME
Console, `gnome-terminal`, `konsole`, `kitty`, `alacritty` — le premier
trouvé) et y lance un script qui :

1. Note la génération système actuelle
2. Exécute `pkexec nixos-rebuild switch --flake /etc/nixos`
3. Si le rebuild réussit et qu'une nouvelle génération a été créée,
   affiche le diff de fermeture (`nix store diff-closures`) entre
   l'ancienne et la nouvelle génération — exactement les paquets
   ajoutés/retirés/modifiés
4. Attend que tu appuies sur **Entrée** avant de fermer la fenêtre

Togglenix ne capture pas cette sortie dans son interface : suis la
progression et le diff directement dans la fenêtre de terminal qui
s'ouvre, puis clique sur **Recharger** (icône ↻) dans Togglenix une
fois terminé pour rafraîchir l'état affiché. Si tu utilises un autre
chemin de flake ou une autre commande de rebuild, modifie la variable
`rebuild_script` dans `pkgs/app.py` (fonction
`_on_apply_clicked`).

## Limites connues (assumées pour cette version)

- Togglenix ne gère qu'un seul mode de toggle : commenter/décommenter
  une ligne de chemin. Les modules qui s'activent uniquement via une
  option `programs.xxx.enable` ne sont pas couverts.
- `pkexec` et la commande de rebuild doivent être disponibles dans le
  `PATH` système au moment du clic sur "Appliquer" (ou lors de
  l'écriture dans un fichier de config appartenant à root).
- La méthode d'installation (`curl | bash`) nécessite que Nix soit
  disponible.
