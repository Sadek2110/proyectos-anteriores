package com.example.data

import com.example.model.*
import kotlin.math.*

object CatalogRepository {

    val pois = listOf(
        Poi(
            id = "murallas",
            name = "Murallas Reales",
            latitude = 35.8885,
            longitude = -5.3210,
            interests = listOf("history", "architecture"),
            source = "https://www.ceuta.es/ceuta/museos-ceuta/murallas-reales",
            narration = LocalizedText(
                es = "Las Murallas Reales forman un conjunto fortificado junto al foso navegable de Ceuta. Observa cómo las defensas delimitan el acceso al centro de la ciudad.",
                en = "The Royal Walls form a fortified complex beside Ceuta’s navigable moat. Look at how the defences frame the entrance to the city centre.",
                fr = "Les Murailles Royales forment un ensemble fortifié au bord du fossé navigable de Ceuta. Observez comment les défenses encadrent l’entrée du centre-ville.",
                ar = "تشكل الأسوار الملكية مجمعاً محصناً بجوار الخندق المائي في سبتة. تأمل كيف تحدد التحصينات مدخل وسط المدينة."
            ),
            detail = LocalizedText(
                es = "Fíjate en la relación entre el agua y la arquitectura defensiva.",
                en = "Notice the relationship between the water and defensive architecture.",
                fr = "Observez la relation entre l’eau et l’architecture défensive.",
                ar = "لاحظ العلاقة بين الماء والعمارة الدفاعية."
            ),
            drawableResName = "ceuta_mar"
        ),
        Poi(
            id = "africa",
            name = "Plaza de África",
            latitude = 35.8883,
            longitude = -5.3185,
            interests = listOf("history"),
            source = "https://www.turismoceuta.com/es/centro",
            narration = LocalizedText(
                es = "La Plaza de África reúne parte del patrimonio monumental de Ceuta. En su entorno se encuentran la catedral y el santuario de Santa María de África.",
                en = "Plaza de África brings together part of Ceuta’s monumental heritage. The cathedral and the sanctuary of Santa María de África stand nearby.",
                fr = "La place d’Afrique rassemble une partie du patrimoine monumental de Ceuta. La cathédrale et le sanctuaire Santa María de África se trouvent à proximité.",
                ar = "تجمع ساحة أفريقيا جانباً من التراث المعماري لسبتة. تقع بالقرب منها الكاتدرائية وكنيسة سانتا ماريا دي أفريقيا."
            ),
            detail = LocalizedText(
                es = "La plaza permite observar varios edificios históricos en un mismo espacio.",
                en = "The square lets you observe several historic buildings in one place.",
                fr = "La place permet d’observer plusieurs bâtiments historiques au même endroit.",
                ar = "تتيح الساحة مشاهدة عدة مبانٍ تاريخية في مكان واحد."
            ),
            drawableResName = "ceuta_calle"
        ),
        Poi(
            id = "dragones",
            name = "Casa de los Dragones",
            latitude = 35.8897,
            longitude = -5.3070,
            interests = listOf("architecture", "history"),
            source = "https://www.ceutaturismo.com/arquitectura-detalle.php?s=casa-dragones",
            narration = LocalizedText(
                es = "La Casa de los Dragones destaca por las figuras de dragones de su cubierta y por su arquitectura ecléctica. Está junto a la Plaza de los Reyes.",
                en = "The House of the Dragons stands out for the dragon figures on its roof and its eclectic architecture. It is next to Plaza de los Reyes.",
                fr = "La Maison des Dragons se distingue par les dragons de sa toiture et son architecture éclectique. Elle se trouve près de la Plaza de los Reyes.",
                ar = "يتميز بيت التنانين بتماثيل التنانين فوق سطحه وبعمارته الانتقائية. يقع بجوار ساحة الملوك."
            ),
            detail = LocalizedText(
                es = "Observa la decoración de la fachada desde el espacio público.",
                en = "Observe the façade decoration from the public space.",
                fr = "Observez le décor de la façade depuis l’espace public.",
                ar = "تأمل زخارف الواجهة من المكان العام."
            ),
            drawableResName = "ceuta_portada"
        )
    )

    val routes = listOf(
        Route(
            id = "ceuta-centro",
            name = LocalizedText(
                es = "Ceuta histórica",
                en = "Historic Ceuta",
                fr = "Ceuta historique",
                ar = "سبتة التاريخية"
            ),
            stops = pois.map { it.id },
            estimatedMinutes = 45
        )
    )

    val emergencySteps = mapOf(
        Language.ES to listOf(
            "En una emergencia, llama al 112.",
            "Indica tu ubicación y explica lo que ocurre al operador.",
            "Sigue sus indicaciones. Para localizar un centro, abre la navegación."
        ),
        Language.EN to listOf(
            "In an emergency, call 112.",
            "Tell the operator your location and what has happened.",
            "Follow their instructions. To locate a centre, open navigation."
        ),
        Language.FR to listOf(
            "En cas d’urgence, appelez le 112.",
            "Indiquez votre position et expliquez la situation à l’opérateur.",
            "Suivez ses instructions. Pour trouver un centre, ouvrez la navigation."
        ),
        Language.AR to listOf(
            "في حالة الطوارئ اتصل بالرقم 112.",
            "أخبر الموظف بموقعك واشرح ما حدث.",
            "اتبع تعليماته. لتحديد موقع مركز افتح تطبيق الملاحة."
        )
    )

    fun directionsUrl(destination: String): String {
        return "https://www.google.com/maps/dir/?api=1&travelmode=walking&destination=" +
                java.net.URLEncoder.encode(destination, "UTF-8")
    }

    val emergencyServices = listOf(
        EmergencyService(
            id = "hospital",
            kind = "hospital",
            name = "Hospital Universitario de Ceuta",
            address = "Calle Loma Colmenar s/n, Ceuta",
            source = "https://www.sanidad.gob.es/ciudadanos/centros.do?metodo=realizarDetalle&numero=510039&tipo=hospital",
            directionsUrl = directionsUrl("Hospital Universitario de Ceuta, Calle Loma Colmenar, Ceuta")
        ),
        EmergencyService(
            id = "police",
            kind = "police",
            name = "Policía Nacional · Ceuta",
            address = "Paseo de Colón 4, Ceuta",
            source = "https://sede.policia.gob.es/portalCiudadano/_es/dependencias_localizador_accesible_provincias.php",
            directionsUrl = directionsUrl("Jefatura Superior de Policía de Ceuta, Paseo de Colón 4, Ceuta")
        ),
        EmergencyService(
            id = "consular",
            kind = "consular",
            name = "Embajadas y consulados extranjeros en España",
            address = "Directorio por nacionalidad · no se presupone una oficina en Ceuta",
            source = "https://www.spain.info/es/consulta/embajadas-espana/",
            directionsUrl = null
        )
    )

    fun distanceMeters(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val rad = Math.PI / 180.0
        val dLat = (lat2 - lat1) * rad
        val dLon = (lon2 - lon1) * rad
        val a = sin(dLat / 2.0).pow(2.0) +
                cos(lat1 * rad) * cos(lat2 * rad) * sin(dLon / 2.0).pow(2.0)
        val c = 2.0 * atan2(sqrt(a), sqrt(max(0.0, 1.0 - a)))
        return 6371000.0 * c
    }

    fun getLocalizedNarration(poi: Poi, lang: Language, interests: Set<String>): String {
        val base = poi.narration.get(lang)
        val extra = if (interests.any { poi.interests.contains(it) }) " " + poi.detail.get(lang) else ""
        return base + extra
    }
}
