# Project Objective

To provide a mapping tool for blind, partially-sighted and fully sighted users which provides spatial geographical, political and other data equally understandable to all users.

# High Level Requirements for a mapping solution for the visually impaired 

* A mapping solution for screen reader users is wanted but the solution should cater for those with no vision, some vision and fully sighted so all users can work with the same tool on an equal footing
* Mapping has a broad meaning here;
** Oceans, seas, continents, regions, countries, 
** Higher granularity of these features such as bays, straits, lakes, political divisions of multiple layrs within countries, physical geography such as deserts, mountain ranges, land use such as farmland, forest, other area designations such as national parks.
** Linear or network features such as rivers, railway lines, roads.  
** the most detailed view is expected to cover road networks within urban areas along with details such as;
*** Nearby areas including school boundaries, parks, large public spaces
*** Points such as bus stops, pedestrian crossings, bins, amenities.
** Information layers such as grids with a z-value within that grid e.g. average rainfull in a 5km square
* It is expected that a standard graphical map will be part of the slution to cater for sighted users but functionality should be skewed towards supporting blind and visually impaired users to get as much information as possible from the solution.
* the target platform as a minimum is Windows but ideally Mac users can be catered for with little additional effort.
* A blind user can be assumed to use a screen reader like NVDA or Jaws, or VoiceOver on Mac.
* Information to be extracted by a user includes:
** Information about a currently focused area such as a sea, country, lake, country park, public space
** Information about a currently focused linear or network feature
** Information about a currently focused point feature
** Information about the currently focused feature's relation to other  areas, linear and point features.
** This includes bordering areas, and linear features, their  distance to nearest point on border, and bearing to nearest point, distance and bearing to points.
** Information for non-adjacent features 
** Information on what is contained within an area, and what a feature is contained within
** Intersections of areas 
* The user must be able to move around the "world" easily traversing large areas and moving with greater granularity over small areas.  Ideally, since the world is a near sphere, the user should be able to move in any direction for any distance though it maybe useful to have multiple movements schemes to simplify navigation.
* Navigation of linear features must also be possible 
* The user must be able to both search and browse for features 
* Sonification is expected to be a useful tool to impart spatial awareness to the user e.g. The distance and bearing of another feature from the current position can be portrayed using HRTF sound.
* Support for touch screens should be considered as one method for imparting information e.g. a user could be given sound feedback when tracing the line of a linear feature, or tracing the outline of an area,  but cannot be considered a primary tool.
* Data needs to be free to collect but should support attribution licensing if required.
* Data size is an open topic. Some users may not tolerate a download of more than 1Gb, whilst keen mappers may be interested to collect more data that grosses much higher space.
* It is expected that the solution will require two parts; a data collection and organising tool used by only a handful of people, and the main mapping application. both need to be screen reader friendly.

