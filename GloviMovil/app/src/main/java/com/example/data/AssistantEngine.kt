package com.example.data

import com.example.model.*
import java.text.Normalizer
import java.util.regex.Pattern

object AssistantEngine {

    fun detectIntent(text: String): String {
        val normalized = Normalizer.normalize(text.lowercase(), Normalizer.Form.NFD)
        val clean = Pattern.compile("\\p{InCombiningDiacriticalMarks}+").matcher(normalized).replaceAll("")

        if (clean.contains("112") || clean.contains("emergen") || clean.contains("urgenc") ||
            clean.contains("ambulanc") || clean.contains("polic") || clean.contains("hospital") ||
            clean.contains("help me") || clean.contains("au secours") || clean.contains("socorro") ||
            clean.contains("طوارئ") || clean.contains("شرطة") || clean.contains("مستشفى") ||
            clean.contains("اسعاف") || clean.contains("إسعاف")
        ) return "emergency"

        if (clean.contains("reserv") || clean.contains("book") || clean.contains("حجز")) return "booking"

        if (clean.contains("comer") || clean.contains("comida") || clean.contains("restaura") ||
            clean.contains("food") || clean.contains("eat") || clean.contains("gastrono") ||
            clean.contains("manger") || clean.contains("طعام") || clean.contains("مطعم")
        ) return "food"

        if (clean.contains("esim") || clean.contains("internet") || clean.contains("datos moviles") ||
            clean.contains("انترنت") || clean.contains("إنترنت")
        ) return "esim"

        return "visit"
    }

    fun getLocalResponse(
        message: String,
        lang: Language,
        interests: Set<String>
    ): Pair<String, List<ChatSource>> {
        val intent = detectIntent(message)
        val sources = CatalogRepository.pois.map { ChatSource(title = it.name, url = it.source) }

        val catalog = CatalogRepository.pois.filter { poi ->
            interests.isEmpty() || poi.interests.any { interests.contains(it) }
        }.ifEmpty { CatalogRepository.pois }

        val descriptions = catalog.joinToString("\n\n") { poi ->
            "${poi.name}: ${CatalogRepository.getLocalizedNarration(poi, lang, interests)}"
        }

        val templates = mapOf(
            "visit" to mapOf(
                Language.ES to "Puedes descubrir Ceuta con estas paradas de la ruta:\n\n",
                Language.EN to "Explore Ceuta through these stops on the route:\n\n",
                Language.FR to "Découvrez Ceuta avec ces étapes du parcours :\n\n",
                Language.AR to "اكتشف سبتة عبر محطات هذا المسار:\n\n"
            ),
            "food" to mapOf(
                Language.ES to "Consulta los servicios de gastronomía en Reservas. Los servicios iniciales son de demostración; no disponemos de horarios ni menús verificados de restaurantes reales.",
                Language.EN to "See food services under Bookings. Initial services are demonstrations; we do not have verified opening hours or menus for real restaurants.",
                Language.FR to "Consultez les services gastronomiques dans Réservations. Les services initiaux sont des démonstrations ; nous ne disposons pas d’horaires ni de menus vérifiés de restaurants réels.",
                Language.AR to "اطلع على خدمات الطعام في الحجوزات. الخدمات الأولية تجريبية؛ لا تتوفر لدينا مواعيد أو قوائم طعام موثقة لمطاعم حقيقية."
            ),
            "booking" to mapOf(
                Language.ES to "Abre Reservas, elige un turno y confirma el número de personas. Puedes consultar y cancelar tus solicitudes. Los servicios DEMO no reservan en negocios reales.",
                Language.EN to "Open Bookings, choose a slot and confirm the party size. You can view and cancel requests. DEMO services do not book real businesses.",
                Language.FR to "Ouvrez Réservations, choisissez un créneau et confirmez le nombre de personnes. Vous pouvez consulter et annuler vos demandes. Les services DEMO ne réservent pas auprès de vrais commerces.",
                Language.AR to "افتح الحجوزات واختر موعداً وأكد عدد الأشخاص. يمكنك عرض الطلبات وإلغاؤها. الخدمات التجريبية لا تحجز في مؤسسات حقيقية."
            ),
            "esim" to mapOf(
                Language.ES to "La compra y activación de eSIM no está disponible en este piloto.",
                Language.EN to "eSIM purchase and activation are not available in this pilot.",
                Language.FR to "L’achat et l’activation d’eSIM ne sont pas disponibles dans ce pilote.",
                Language.AR to "شراء وتفعيل الشريحة الإلكترونية غير متاحين في هذه النسخة التجريبية."
            )
        )

        return when (intent) {
            "emergency" -> {
                val text = (CatalogRepository.emergencySteps[lang] ?: emptyList()).joinToString(" ")
                val emSources = listOf(ChatSource("112 Ceuta", "https://www.ceuta.es/112/index.html"))
                Pair(text, emSources)
            }
            "visit" -> {
                val header = templates["visit"]?.get(lang) ?: ""
                Pair(header + descriptions, sources)
            }
            else -> {
                val text = templates[intent]?.get(lang) ?: ""
                Pair(text, emptyList())
            }
        }
    }
}
